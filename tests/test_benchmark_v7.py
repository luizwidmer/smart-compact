from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from scripts.benchmark_v7 import (
    ARM_SPECS,
    DEFAULT_CASES,
    _latest_agent_message,
    _new_trace,
    _read_child_threads,
    aggregate_arms,
    aggregate_comparisons,
    build_arm_config,
    checkpoint_payload,
    comparison_rows,
    evaluate_delegation,
    expected_result_keys,
    load_cases,
    matrix_exit_code,
    parse_partition_ids,
    publication_status,
    sort_results,
    write_json_payload,
)


def compliant_brief(case: dict, partition_ids: list[str]) -> str:
    partitions = {item["id"]: item for item in case["delegation"]["expected_partitions"]}
    markers = [
        marker
        for partition_id in partition_ids
        for marker in partitions[partition_id]["markers"]
    ]
    return (
        "The inherited working directory is already the exact target root; "
        "shell cd/chdir is forbidden. Every command string's first word must be literal `rtk`.\n"
        f"partition_ids: {', '.join(partition_ids)}\n"
        + "\n".join(markers)
    )


def trace_for(
    case: dict,
    assignments: dict[str, list[str]],
    *,
    changes: dict[str, list[str]] | None = None,
    statuses: dict[str, str] | None = None,
    roles: dict[str, str] | None = None,
    parent_changes: list[str] | None = None,
    child_commands: dict[str, list[str]] | None = None,
    child_messages: dict[str, str] | None = None,
    parent_commands: list[str] | None = None,
) -> dict:
    child_ids = sorted(assignments)
    statuses = statuses or {child_id: "completed" for child_id in child_ids}
    roles = roles or {child_id: "spark_worker" for child_id in child_ids}
    file_changes = {child_id: [] for child_id in child_ids}
    file_changes.update(changes or {})
    if parent_changes is not None:
        file_changes["parent"] = parent_changes
    if child_messages is None:
        partitions = {item["id"]: item for item in case["delegation"]["expected_partitions"]}
        child_messages = {
            child_id: "\n".join(
                marker
                for partition_id in partition_ids
                for marker in partitions[partition_id]["markers"]
            )
            for child_id, partition_ids in assignments.items()
        }
    commands = {child_id: [] for child_id in child_ids}
    commands.update(child_commands or {})
    if parent_commands is not None:
        commands["parent"] = parent_commands
    return {
        "child_thread_ids": child_ids,
        "child_roles": roles,
        "child_paths": {},
        "child_turn_statuses": statuses,
        "spawn_records": {
            child_id: {"prompt": compliant_brief(case, partition_ids), "model": "spark"}
            for child_id, partition_ids in assignments.items()
        },
        "usage_by_thread": {child_id: {"totalTokens": 10} for child_id in child_ids},
        "item_counts_by_thread": {child_id: {"agentMessage": 1} for child_id in child_ids},
        "child_final_messages": child_messages,
        "commands_by_thread": commands,
        "file_changes_by_thread": file_changes,
        "peak_concurrency": len(child_ids),
    }


class ManifestTests(unittest.TestCase):
    def test_default_schema_v2_manifest_validates(self) -> None:
        cases = load_cases(DEFAULT_CASES)

        self.assertGreaterEqual(len(cases), 6)
        self.assertTrue(any(case["delegation"]["mode"] == "forbidden" for case in cases))
        self.assertTrue(
            any(case["delegation"]["spawned_workers"]["max"] > 1 for case in cases)
        )

    def test_manifest_rejects_invalid_delegation_contract(self) -> None:
        payload = json.loads(DEFAULT_CASES.read_text(encoding="utf-8"))
        payload["cases"][1]["delegation"]["worker_io"] = "shared_write"
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "bad.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "worker_io"):
                load_cases(path)

        payload = json.loads(DEFAULT_CASES.read_text(encoding="utf-8"))
        payload["cases"][1]["delegation"]["expected_partitions"][0]["weight"] = 1.5
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "bad-weight.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "partition weight"):
                load_cases(path)


class DelegationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cases = {case["id"]: case for case in load_cases(DEFAULT_CASES)}

    def test_partition_parser_requires_literal_marker_and_known_ids(self) -> None:
        expected = {"logs-ab", "logs-cd"}
        self.assertEqual(
            parse_partition_ids("partition_ids: logs-ab, logs-cd", expected),
            (["logs-ab", "logs-cd"], True),
        )
        self.assertEqual(parse_partition_ids("partitions: logs-ab", expected), ([], False))
        self.assertEqual(parse_partition_ids("partition_ids: unknown", expected), ([], False))

    def test_latest_agent_message_uses_the_last_completed_turn_item(self) -> None:
        turns = [
            {"items": [{"type": "agentMessage", "text": "first"}]},
            {
                "items": [
                    {"type": "commandExecution", "command": "rtk pwd"},
                    {"type": "agentMessage", "text": "final"},
                ]
            },
        ]

        self.assertEqual(_latest_agent_message(turns), "final")

    def test_child_thread_read_captures_completed_final_message(self) -> None:
        class Client:
            @staticmethod
            def request(request_id: int, method: str, params: dict) -> dict:
                del request_id, method, params
                return {
                    "thread": {
                        "agentRole": "spark_worker",
                        "turns": [
                            {
                                "status": "completed",
                                "startedAt": 1,
                                "completedAt": 2,
                                "items": [
                                    {"type": "agentMessage", "text": "logs/shard-a.log"}
                                ],
                            }
                        ],
                    }
                }

        state = _new_trace()
        state["child_ids"].add("child")

        next_request_id = _read_child_threads(Client(), state, 100)

        self.assertEqual(next_request_id, 101)
        self.assertEqual(state["child_turn_statuses"]["child"], "completed")
        self.assertEqual(state["child_final_messages"]["child"], "logs/shard-a.log")

    def test_adaptive_routing_accepts_two_workers_covering_three_partitions(self) -> None:
        case = self.cases["incident-triage"]
        trace = trace_for(case, {"one": ["logs-ab", "logs-cd"], "two": ["logs-ef"]})

        result = evaluate_delegation(case, ARM_SPECS["v7-spark"], trace)

        self.assertTrue(result["routing_ok"], result)
        self.assertEqual(result["actual_spawned_workers"], 2)
        self.assertEqual(result["useful_worker_count"], 2)
        self.assertEqual(result["useful_worker_rate"], 1.0)
        self.assertEqual(result["duplicate_work_ratio"], 0.0)

    def test_read_only_requires_evidence_for_every_assigned_source_marker(self) -> None:
        case = self.cases["incident-triage"]
        assignments = {"one": ["logs-ab", "logs-cd"], "two": ["logs-ef"]}
        trace = trace_for(
            case,
            assignments,
            child_messages={
                "one": "logs/shard-a.log.bak logs/shard-b.log.bak",
                "two": "no source paths",
            },
        )

        result = evaluate_delegation(case, ARM_SPECS["v7-spark"], trace)

        self.assertTrue(result["partition_claim_coverage_ok"])
        self.assertFalse(result["partition_coverage_ok"])
        self.assertFalse(result["worker_evidence_coverage_ok"])
        self.assertEqual(result["child_evidence_markers"]["one"], [])
        self.assertEqual(
            result["child_missing_evidence_markers"]["two"],
            ["logs/shard-e.log", "logs/shard-f.log"],
        )
        self.assertEqual(result["useful_worker_count"], 0)
        self.assertFalse(result["routing_ok"])

    def test_read_only_combines_command_and_completed_message_evidence(self) -> None:
        case = self.cases["incident-triage"]
        assignments = {"one": ["logs-ab", "logs-cd"], "two": ["logs-ef"]}
        trace = trace_for(
            case,
            assignments,
            child_commands={
                "one": ["rtk sed -n 1,80p logs/shard-a.log logs/shard-b.log"],
                "two": ["rtk sed -n 1,80p /tmp/work/logs/shard-e.log"],
            },
            child_messages={
                "one": "Verified logs/shard-c.log and logs/shard-d.log.",
                "two": "Verified logs/shard-f.log.",
            },
        )
        trace["item_counts_by_thread"]["one"] = {}

        result = evaluate_delegation(case, ARM_SPECS["v7-spark"], trace)

        self.assertTrue(result["worker_evidence_coverage_ok"], result)
        self.assertTrue(all(result["child_evidence_coverage_ok"].values()))
        self.assertEqual(result["useful_worker_count"], 2)
        self.assertTrue(result["routing_ok"], result)

    def test_duplicate_partition_and_nonuseful_worker_fail_routing(self) -> None:
        case = self.cases["incident-triage"]
        duplicate = trace_for(
            case,
            {"one": ["logs-ab", "logs-cd"], "two": ["logs-ab", "logs-ef"]},
        )
        result = evaluate_delegation(case, ARM_SPECS["v7-spark"], duplicate)
        self.assertFalse(result["partition_replication_ok"])
        self.assertFalse(result["routing_ok"])

        nonuseful = trace_for(case, {"one": ["logs-ab", "logs-cd"], "two": ["logs-ef"]})
        nonuseful["item_counts_by_thread"]["two"] = {}
        nonuseful["child_final_messages"].pop("two")
        result = evaluate_delegation(case, ARM_SPECS["v7-spark"], nonuseful)
        self.assertEqual(result["useful_worker_count"], 1)
        self.assertFalse(result["useful_worker_range_ok"])
        self.assertFalse(result["routing_ok"])

    def test_wrong_role_or_incomplete_child_fails(self) -> None:
        case = self.cases["incident-triage"]
        assignments = {"one": ["logs-ab", "logs-cd"], "two": ["logs-ef"]}
        wrong_role = trace_for(case, assignments, roles={"one": "spark_worker", "two": "other"})
        self.assertFalse(
            evaluate_delegation(case, ARM_SPECS["v7-spark"], wrong_role)["routing_ok"]
        )
        incomplete = trace_for(
            case, assignments, statuses={"one": "completed", "two": "failed"}
        )
        result = evaluate_delegation(case, ARM_SPECS["v7-spark"], incomplete)
        self.assertFalse(result["child_completion_ok"])
        self.assertFalse(result["routing_ok"])

    def test_path_disjoint_rejects_cross_partition_reserved_and_parent_overlap(self) -> None:
        case = self.cases["monorepo-sdk-migration"]
        assignments = {
            "one": ["packages-ab", "packages-cd"],
            "two": ["packages-ef", "packages-gh"],
        }
        valid_changes = {
            "one": ["packages/a_create.py"],
            "two": ["packages/e_bulk_create.py"],
        }
        valid = trace_for(case, assignments, changes=valid_changes)
        self.assertTrue(
            evaluate_delegation(case, ARM_SPECS["v7-spark"], valid, "parent")["routing_ok"]
        )

        cross = trace_for(
            case,
            assignments,
            changes={"one": ["packages/e_bulk_create.py"], "two": ["packages/e_bulk_update.py"]},
        )
        result = evaluate_delegation(case, ARM_SPECS["v7-spark"], cross, "parent")
        self.assertFalse(result["child_io_ok"]["one"])
        self.assertFalse(result["routing_ok"])

        reserved = trace_for(
            case,
            assignments,
            changes={"one": ["migration_report.json"], "two": ["packages/e_bulk_create.py"]},
        )
        self.assertFalse(
            evaluate_delegation(case, ARM_SPECS["v7-spark"], reserved, "parent")[
                "worker_io_ok"
            ]
        )

        overlap = trace_for(
            case,
            assignments,
            changes=valid_changes,
            parent_changes=["packages/a_create.py", "migration_report.json"],
        )
        result = evaluate_delegation(case, ARM_SPECS["v7-spark"], overlap, "parent")
        self.assertEqual(result["parent_worker_overlap_paths"], ["packages/a_create.py"])
        self.assertFalse(result["parent_worker_overlap_ok"])
        self.assertFalse(result["routing_ok"])

    def test_path_disjoint_rejects_parent_exact_marker_reads(self) -> None:
        case = self.cases["monorepo-sdk-migration"]
        assignments = {
            "one": ["packages-ab", "packages-cd"],
            "two": ["packages-ef", "packages-gh"],
        }
        changes = {
            "one": ["packages/a_create.py"],
            "two": ["packages/e_bulk_create.py"],
        }
        acceptance_only = trace_for(
            case,
            assignments,
            changes=changes,
            parent_commands=["rtk proxy python3 -m unittest discover -s tests -v"],
        )
        valid = evaluate_delegation(
            case, ARM_SPECS["v7-spark"], acceptance_only, "parent"
        )
        self.assertTrue(valid["parent_worker_read_overlap_ok"], valid)
        self.assertTrue(valid["routing_ok"], valid)

        exact_read = trace_for(
            case,
            assignments,
            changes=changes,
            parent_commands=["rtk sed -n 1,80p packages/a_create.py migration_report.json"],
        )
        result = evaluate_delegation(
            case, ARM_SPECS["v7-spark"], exact_read, "parent"
        )
        self.assertEqual(
            result["parent_worker_read_overlap_paths"], ["packages/a_create.py"]
        )
        self.assertFalse(result["parent_worker_read_overlap_ok"])
        self.assertTrue(result["parent_worker_overlap_ok"])
        self.assertFalse(result["routing_ok"])

    def test_path_disjoint_worker_without_change_is_not_useful(self) -> None:
        case = self.cases["monorepo-sdk-migration"]
        assignments = {
            "one": ["packages-ab", "packages-cd"],
            "two": ["packages-ef", "packages-gh"],
        }
        trace = trace_for(
            case,
            assignments,
            changes={"one": [], "two": ["packages/e_bulk_create.py"]},
        )
        result = evaluate_delegation(case, ARM_SPECS["v7-spark"], trace, "parent")
        self.assertEqual(result["useful_worker_count"], 1)
        self.assertNotIn("one", result["useful_worker_ids"])
        self.assertEqual(result["useful_worker_rate"], 0.5)

    def test_path_disjoint_uses_observed_writes_instead_of_repeated_prompt_paths(self) -> None:
        case = self.cases["monorepo-sdk-migration"]
        partition_ids = ["packages-ab", "packages-cd", "packages-ef", "packages-gh"]
        trace = trace_for(
            case,
            {"one": partition_ids},
            changes={"one": ["packages/a_create.py"]},
        )
        trace["spawn_records"]["one"]["prompt"] = (
            "The inherited working directory is already the exact target root; "
            "shell cd/chdir is forbidden. Every command string's first word must be "
            "literal `rtk`.\npartition_ids: " + ", ".join(partition_ids)
        )

        result = evaluate_delegation(case, ARM_SPECS["v7-spark"], trace, "parent")

        self.assertFalse(result["partition_markers_ok"])
        self.assertTrue(result["partition_prompt_marker_gate_ok"])
        self.assertTrue(result["routing_ok"], result)

    def test_no_spark_uses_zero_effective_expectation(self) -> None:
        case = self.cases["incident-triage"]
        trace = trace_for(case, {})
        result = evaluate_delegation(case, ARM_SPECS["v7-no-spark"], trace, "parent")
        self.assertTrue(result["routing_ok"], result)
        self.assertEqual(result["actual_spawned_workers"], 0)


class MetricsAndCheckpointTests(unittest.TestCase):
    @staticmethod
    def row(arm: str, parent_tokens: int, workers: int, useful: int) -> dict:
        return {
            "case_id": "case",
            "trial": 1,
            "arm": arm,
            "success": True,
            "grade": {"ok": True, "passed": 1, "total": 1, "score_pct": 100.0},
            "usage_complete": True,
            "routing_ok": True,
            "parent_total_tokens": parent_tokens,
            "child_total_tokens": workers * 10,
            "combined_total_tokens": parent_tokens + workers * 10,
            "execution_duration_seconds": 10.0,
            "actual_spawned_workers": workers,
            "useful_worker_count": useful,
            "useful_worker_rate": useful / workers if workers else 0.0,
            "peak_concurrency": workers,
        }

    def test_generic_primary_comparison_and_worker_efficiency(self) -> None:
        baseline = self.row("v6-spark", 100, 1, 1)
        candidate = self.row("v7-spark", 60, 2, 1)

        rows = comparison_rows([candidate, baseline], ["v6-spark", "v7-spark"])
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertTrue(row["primary"])
        self.assertEqual(row["parent_tokens_saved"], 40)
        self.assertEqual(row["parent_token_reduction_pct"], 40.0)
        self.assertEqual(row["parent_tokens_saved_per_spawned_worker"], 20.0)
        self.assertEqual(row["parent_tokens_saved_per_useful_worker"], 40.0)
        self.assertEqual(row["primary_efficiency_metric"], "parent_tokens_saved_per_spawned_worker")
        self.assertEqual(row["primary_efficiency_value"], 20.0)
        self.assertEqual(row["spawned_worker_count"], 2)
        self.assertEqual(row["worker_count"], 2)
        self.assertEqual(row["selection_winner"], "candidate")

        aggregate = aggregate_comparisons(rows)["v6_to_v7_spark"]
        self.assertEqual(aggregate["parent_token_pairs"], 1)
        self.assertEqual(
            aggregate["primary_efficiency_metric"],
            "parent_tokens_saved_per_spawned_worker",
        )
        self.assertEqual(aggregate["median_primary_efficiency"], 20.0)
        self.assertEqual(aggregate["median_spawned_worker_count"], 2)
        self.assertEqual(aggregate["median_worker_count"], 2)
        self.assertEqual(aggregate["spawned_worker_count_curve"][0]["spawned_worker_count"], 2)
        self.assertEqual(aggregate["spawned_worker_count_curve"][0]["median_primary_efficiency"], 20.0)
        self.assertEqual(aggregate["worker_count_curve"][0]["worker_count"], 2)

        arm_summary = aggregate_arms([candidate, baseline], ["v6-spark", "v7-spark"])
        self.assertEqual(arm_summary["by_arm"]["v7-spark"]["median_spawned_worker_count"], 2)
        self.assertEqual(arm_summary["by_arm"]["v7-spark"]["median_worker_count"], 2)

    def test_fewer_spawned_workers_win_when_parent_savings_are_equal(self) -> None:
        baseline = self.row("v6-spark", 60, 2, 2)
        candidate = self.row("v7-spark", 60, 1, 1)

        comparison = comparison_rows([baseline, candidate], ["v6-spark", "v7-spark"])[0]
        self.assertEqual(comparison["parent_tokens_saved"], 0)
        self.assertEqual(comparison["selection_winner"], "candidate")

        ranking = aggregate_arms([baseline, candidate], ["v6-spark", "v7-spark"])[
            "selection_ranking"
        ]
        self.assertEqual([row["arm"] for row in ranking], ["v7-spark", "v6-spark"])
        self.assertEqual(ranking[0]["median_spawned_worker_count"], 1)

    def test_useful_worker_count_does_not_change_ranking(self) -> None:
        baseline = self.row("v6-spark", 60, 2, 2)
        candidate = self.row("v7-spark", 60, 2, 1)

        first = aggregate_arms([baseline, candidate], ["v6-spark", "v7-spark"])[
            "selection_ranking"
        ]
        candidate["useful_worker_count"] = 2
        candidate["useful_worker_rate"] = 1.0
        second = aggregate_arms([baseline, candidate], ["v6-spark", "v7-spark"])[
            "selection_ranking"
        ]

        self.assertEqual([row["arm"] for row in first], [row["arm"] for row in second])
        self.assertEqual(
            comparison_rows([baseline, candidate], ["v6-spark", "v7-spark"])[0][
                "selection_winner"
            ],
            "tie",
        )

    def test_zero_spawned_workers_have_no_per_worker_efficiency(self) -> None:
        baseline = self.row("v6-spark", 100, 0, 0)
        candidate = self.row("v7-spark", 90, 0, 0)

        row = comparison_rows([baseline, candidate], ["v6-spark", "v7-spark"])[0]
        self.assertEqual(row["parent_tokens_saved"], 10)
        self.assertIsNone(row["parent_tokens_saved_per_spawned_worker"])
        self.assertIsNone(row["parent_tokens_saved_per_useful_worker"])
        self.assertIsNone(row["primary_efficiency_value"])

        aggregate = aggregate_comparisons([row])["v6_to_v7_spark"]
        self.assertIsNone(aggregate["median_primary_efficiency"])
        self.assertEqual(aggregate["median_spawned_worker_count"], 0)

    def test_sort_and_atomic_per_arm_checkpoint(self) -> None:
        rows = [
            {"case_id": "second", "trial": 1, "arm": "v7-spark"},
            {"case_id": "first", "trial": 1, "arm": "v7-spark"},
            {"case_id": "first", "trial": 1, "arm": "v6-spark"},
        ]
        ordered = sort_results(rows, ["first", "second"], ["v6-spark", "v7-spark"])
        self.assertEqual(
            [(row["case_id"], row["arm"]) for row in ordered],
            [("first", "v6-spark"), ("first", "v7-spark"), ("second", "v7-spark")],
        )
        payload = checkpoint_payload(
            results=ordered[:1],
            selected_arms=["v6-spark", "v7-spark"],
            execution_order=[],
            repetitions=1,
            jobs=3,
        )
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "checkpoint.json"
            write_json_payload(path, payload)
            observed = json.loads(path.read_text(encoding="utf-8"))
        self.assertFalse(observed["complete"])
        self.assertEqual(observed["completed_arms"], 1)

    def test_one_arm_exploratory_success_needs_no_pair(self) -> None:
        result = self.row("v7-spark", 60, 2, 2)
        cases = [{"id": "case"}]
        expected = expected_result_keys(cases, 1, ["v7-spark"])
        status = publication_status([result], expected, repetitions=1, jobs=3)

        self.assertTrue(status["matrix_complete"])
        self.assertFalse(status["quality_publishable"])
        self.assertFalse(status["token_publishable"])
        self.assertFalse(status["latency_publishable"])
        self.assertEqual(comparison_rows([result], ["v7-spark"]), [])
        self.assertEqual(matrix_exit_code([result], status["matrix_complete"]), 0)

    def test_v6_skill_is_explicit_input_only_and_v7_is_standalone(self) -> None:
        self.assertTrue(ARM_SPECS["v6-spark"].skill_input)
        self.assertFalse(ARM_SPECS["v7-spark"].skill_input)
        config = build_arm_config(ARM_SPECS["v6-spark"], {})
        policy_text = ARM_SPECS["v6-spark"].policy_path.read_text(encoding="utf-8")
        self.assertNotIn(policy_text, config["developer_instructions"])


if __name__ == "__main__":
    unittest.main()
