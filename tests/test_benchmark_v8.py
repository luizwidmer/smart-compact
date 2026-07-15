from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import scripts.benchmark_v8 as benchmark_v8

from scripts.benchmark_v8 import (
    ARM_SPECS,
    DEFAULT_ARMS,
    DEFAULT_CASES,
    build_arm_config,
    build_forced_worker_config,
    comparison_rows,
    collect_forced_pair,
    evaluate_delegation,
    expected_result_keys,
    forced_worker_prompt,
    load_cases,
    parse_partition_ids,
    publication_status,
    prepare_v8_codex_home,
    validate_v8_fixtures,
)


def brief(partition_ids: list[str]) -> str:
    return (
        f"partition_ids: {', '.join(partition_ids)}\n"
        "paths: exclusive assigned paths\n"
        "task: mechanical work\n"
        "return: concise evidence"
    )


def trace_for(
    case: dict,
    assignments: dict[str, list[str]],
    *,
    statuses: dict[str, str] | None = None,
    messages: dict[str, str] | None = None,
    prompts: dict[str, str] | None = None,
) -> dict:
    child_ids = sorted(assignments)
    partitions = {item["id"]: item for item in case["delegation"]["expected_partitions"]}
    statuses = statuses or {child_id: "completed" for child_id in child_ids}
    if messages is None:
        messages = {
            child_id: "\n".join(
                partitions[partition_id]["markers"][0]
                for partition_id in partition_ids
            )
            for child_id, partition_ids in assignments.items()
        }
    prompts = prompts or {
        child_id: brief(partition_ids) for child_id, partition_ids in assignments.items()
    }
    return {
        "child_thread_ids": child_ids,
        "child_roles": {child_id: "spark_worker" for child_id in child_ids},
        "child_paths": {},
        "child_turn_statuses": statuses,
        "spawn_records": {
            child_id: {
                "prompt": prompts[child_id],
                "model": "gpt-5.3-codex-spark",
                "origin": "parent_agent",
                "native_agent_role": True,
            }
            for child_id in child_ids
        },
        "usage_by_thread": {child_id: {"totalTokens": 10} for child_id in child_ids},
        "item_counts_by_thread": {child_id: {"agentMessage": 1} for child_id in child_ids},
        "child_final_messages": messages,
        "commands_by_thread": {child_id: [] for child_id in child_ids},
        "file_changes_by_thread": {child_id: [] for child_id in child_ids},
        "peak_concurrency": len(child_ids),
    }


class ManifestAndArmTests(unittest.TestCase):
    def test_arm_surface_has_v8_defaults_and_no_v7(self) -> None:
        self.assertEqual(
            DEFAULT_ARMS,
            ("v8-no-spark", "v8-spark-forced", "v8-spark-auto"),
        )
        self.assertEqual(
            set(ARM_SPECS),
            {
                "standard-no-spark",
                "v6-no-spark",
                "v8-no-spark",
                "v8-spark-forced",
                "v8-spark-auto",
            },
        )
        self.assertFalse(any("v7" in arm for arm in ARM_SPECS))

    def test_required_worker_ranges_accept_null_max(self) -> None:
        payload = json.loads(DEFAULT_CASES.read_text(encoding="utf-8"))
        delegation = next(
            case["delegation"]
            for case in payload["cases"]
            if case["delegation"]["mode"] == "required_when_available"
        )
        delegation["spawned_workers"]["max"] = None
        delegation["useful_workers"]["max"] = None
        delegation["peak_concurrency"]["max"] = None
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "cases.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            self.assertEqual(len(load_cases(path)), len(payload["cases"]))

    def test_confirmation_cases_have_no_artificial_worker_cap(self) -> None:
        confirmation = DEFAULT_CASES.with_name("agentic-v8-confirmation.json")
        for case in load_cases(confirmation):
            if case["delegation"]["mode"] != "required_when_available":
                continue
            for field in ("spawned_workers", "useful_workers", "peak_concurrency"):
                with self.subTest(case=case["id"], field=field):
                    self.assertEqual(case["delegation"][field]["min"], 1)
                    self.assertIsNone(case["delegation"][field]["max"])

    def test_required_cases_request_immediate_parseable_partition_briefs(self) -> None:
        manifests = (
            DEFAULT_CASES,
            DEFAULT_CASES.with_name("agentic-v8-heldout.json"),
            DEFAULT_CASES.with_name("agentic-v8-confirmation.json"),
        )
        for manifest in manifests:
            for case in load_cases(manifest):
                if case["delegation"]["mode"] != "required_when_available":
                    continue
                with self.subTest(manifest=manifest.name, case=case["id"]):
                    self.assertIn("Spawn before inspecting assigned paths.", case["prompt"])
                    self.assertIn("`partition_ids: <assigned IDs>`", case["prompt"])
                    self.assertNotIn("parent_work_replaced:", case["prompt"])

    def test_v6_is_explicit_input_and_v8_is_profile_native(self) -> None:
        self.assertTrue(ARM_SPECS["v6-no-spark"].skill_input)
        self.assertFalse(ARM_SPECS["v8-no-spark"].skill_input)
        config = build_arm_config(ARM_SPECS["v6-no-spark"], {})
        policy = ARM_SPECS["v6-no-spark"].policy_path.read_text(encoding="utf-8")
        self.assertNotIn(policy, config["developer_instructions"])

    def test_v8_profile_requires_immediate_partitioned_spawn(self) -> None:
        config = build_arm_config(
            ARM_SPECS["v8-spark-auto"],
            benchmark_v8.load_profile(ARM_SPECS["v8-spark-auto"].profile_path),
        )
        instructions = config["developer_instructions"]
        self.assertIn("delegate.required=spawn_first,before_worker_path_read", instructions)
        self.assertIn("brief=partition_ids_first", instructions)
        self.assertNotIn("parent_work_replaced:", instructions)

    def test_only_spark_arm_declares_preflight_availability(self) -> None:
        profile = benchmark_v8.load_profile(ARM_SPECS["v8-spark-auto"].profile_path)
        spark = build_arm_config(ARM_SPECS["v8-spark-auto"], profile)
        forced = build_arm_config(ARM_SPECS["v8-spark-forced"], profile)
        no_spark = build_arm_config(ARM_SPECS["v8-no-spark"], profile)
        marker = "spark.available=true"
        self.assertIn(marker, spark["developer_instructions"])
        self.assertNotIn(marker, forced["developer_instructions"])
        self.assertNotIn(marker, no_spark["developer_instructions"])
        self.assertIn("spark.brief=partition_ids_first", spark["developer_instructions"])
        self.assertIn("agent_type:spark_worker", spark["developer_instructions"])
        self.assertIn("fork_context:false", spark["developer_instructions"])

    def test_no_spark_model_visible_config_is_frozen(self) -> None:
        spec = ARM_SPECS["v8-no-spark"]
        config = build_arm_config(spec, benchmark_v8.load_profile(spec.profile_path))
        normalized = copy.deepcopy(config)
        for entry in normalized["skills"]["config"]:
            if entry.get("path") == str(benchmark_v8.INSTALLED_SKILL):
                entry["path"] = "<INSTALLED_SKILL>"
        rendered = json.dumps(
            normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        self.assertEqual(
            hashlib.sha256(rendered).hexdigest(),
            "8c25d5f2343bb543533fa39f9f00be1a94c89240630140d7e29f52e8000c8616",
        )

    def test_forced_worker_binds_frozen_model_effort_and_instructions(self) -> None:
        profile = benchmark_v8.load_profile(ARM_SPECS["v8-spark-forced"].profile_path)
        config, identity = build_forced_worker_config(profile)
        self.assertEqual(identity["role"], "spark_worker")
        self.assertEqual(identity["model"], "gpt-5.3-codex-spark")
        self.assertEqual(config["model"], identity["model"])
        self.assertEqual(config["model_reasoning_effort"], identity["effort"])
        self.assertFalse(config["features"]["multi_agent"])

    def test_forced_worker_prompt_is_terse_machine_contract(self) -> None:
        case = next(
            case for case in load_cases(DEFAULT_CASES) if case["id"] == "monorepo-sdk-migration"
        )
        prompt = forced_worker_prompt(case)
        expected_ids = {
            partition["id"] for partition in case["delegation"]["expected_partitions"]
        }
        assigned, syntax_ok = parse_partition_ids(prompt, expected_ids)
        self.assertTrue(syntax_ok)
        self.assertEqual(assigned, sorted(expected_ids))
        self.assertEqual(prompt.lower().count("partition_ids:"), 1)
        self.assertLessEqual(len(prompt.split()), 20)
        self.assertLessEqual(len(prompt.splitlines()), 9)
        self.assertLessEqual(len(prompt.encode("utf-8")), 1200)
        self.assertNotIn(case["prompt"], prompt)
        self.assertNotIn("Original task:", prompt)
        self.assertIn(
            "deny_write=migration_report.json,src/sdk/client.py,tests/test_sdk_migration.py,all_except_rw",
            prompt,
        )
        self.assertIn("ro=src/sdk/client.py,tests/test_sdk_migration.py", prompt)
        self.assertIn("mode=edit", prompt)
        self.assertNotIn("unittest", prompt)
        self.assertIn("client_method_signature,keyword_arguments", prompt)
        self.assertIn("acceptance=compileall;adapter_tests_from_ro(exclude=parent_report)", prompt)
        for partition in case["delegation"]["expected_partitions"]:
            for marker in partition["markers"]:
                self.assertIn(marker, prompt)

    def test_spark_home_uses_frozen_repository_agent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            frozen = root / "frozen-spark.toml"
            frozen.write_text('name = "spark_worker"\nmodel = "gpt-5.3-codex-spark"\n')

            def stale_home(target: Path, spark_enabled: bool) -> Path:
                target.mkdir()
                agents = target / "agents"
                agents.mkdir()
                (agents / "spark-worker.toml").write_text("stale = true\n")
                self.assertTrue(spark_enabled)
                return target

            with patch.object(benchmark_v8, "SPARK_AGENT", frozen), patch.object(
                benchmark_v8, "prepare_codex_home", side_effect=stale_home
            ):
                home = prepare_v8_codex_home(root / "home", True)
            self.assertEqual(
                (home / "agents" / "spark-worker.toml").read_bytes(),
                frozen.read_bytes(),
            )

    def test_development_fixtures_reset_and_gold_acceptance_pass(self) -> None:
        result = validate_v8_fixtures(load_cases(DEFAULT_CASES))
        self.assertTrue(result["ok"], result)
        self.assertTrue(all(row["reset_reproducible"] for row in result["cases"]))
        self.assertTrue(all(row["gold_acceptance_ok"] for row in result["cases"]))


class DelegationGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cases = {case["id"]: case for case in load_cases(DEFAULT_CASES)}

    def test_read_only_evidence_does_not_require_paths_repeated_in_brief(self) -> None:
        case = self.cases["incident-triage"]
        assignments = {"one": ["logs-ab", "logs-cd"], "two": ["logs-ef"]}
        result = evaluate_delegation(
            case,
            ARM_SPECS["v8-spark-auto"],
            trace_for(case, assignments),
            "parent",
        )
        self.assertFalse(result["partition_markers_ok"])
        self.assertTrue(result["partition_prompt_marker_gate_ok"])
        self.assertTrue(result["routing_ok"], result)

    def test_parent_source_overlap_disproves_work_replacement(self) -> None:
        case = self.cases["incident-triage"]
        assignments = {"one": ["logs-ab", "logs-cd", "logs-ef"]}
        trace = trace_for(case, assignments)
        trace["commands_by_thread"]["parent"] = ["rtk cat logs/shard-a.log"]
        result = evaluate_delegation(
            case,
            ARM_SPECS["v8-spark-auto"],
            trace,
            "parent",
        )
        self.assertFalse(result["parent_work_replaced_ok"])
        self.assertFalse(result["routing_ok"])


class ForcedCollectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cases = {case["id"]: case for case in load_cases(DEFAULT_CASES)}

    def test_concurrent_pair_binds_usage_and_consumes_capsule(self) -> None:
        usage = {
            "inputTokens": 8,
            "cachedInputTokens": 0,
            "outputTokens": 2,
            "reasoningOutputTokens": 1,
            "totalTokens": 10,
        }

        class FakeClient:
            def __init__(self, notifications: list[dict]) -> None:
                self.notifications = notifications

            def next_notification(self, _timeout: float) -> dict:
                return self.notifications.pop(0)

            def poll_notification(self, _timeout: float) -> dict | None:
                return self.notifications.pop(0) if self.notifications else None

        with tempfile.TemporaryDirectory() as temporary:
            capsule = Path(temporary) / "capsule.txt"
            notifications = [
                {
                    "method": "item/completed",
                    "params": {
                        "threadId": "worker",
                        "item": {"type": "agentMessage", "text": "logs/shard-a.log"},
                    },
                },
                {
                    "method": "thread/tokenUsage/updated",
                    "params": {"threadId": "worker", "tokenUsage": {"total": usage}},
                },
                {
                    "method": "turn/completed",
                    "params": {"threadId": "worker", "turn": {"status": "completed"}},
                },
                {
                    "method": "item/completed",
                    "params": {
                        "threadId": "parent",
                        "item": {
                            "type": "commandExecution",
                            "command": f"rtk cat {capsule}",
                        },
                    },
                },
                {
                    "method": "item/completed",
                    "params": {
                        "threadId": "parent",
                        "item": {"type": "agentMessage", "text": "done"},
                    },
                },
                {
                    "method": "thread/tokenUsage/updated",
                    "params": {"threadId": "parent", "tokenUsage": {"total": usage}},
                },
                {
                    "method": "turn/completed",
                    "params": {"threadId": "parent", "turn": {"status": "completed"}},
                },
            ]
            started = time.monotonic()
            trace = collect_forced_pair(
                FakeClient(notifications),
                parent_id="parent",
                worker_id="worker",
                worker_prompt_text="partition_ids: logs-ab",
                worker_identity={
                    "role": "spark_worker",
                    "model": "gpt-5.3-codex-spark",
                    "effort": "medium",
                    "agent_sha256": "agent",
                    "instructions_sha256": "instructions",
                    "config_sha256": "config",
                },
                capsule_path=capsule,
                started=started,
                first_spawn_seconds=0.01,
                turn_timeout=2,
                drain_timeout=0.25,
            )
            self.assertEqual(capsule.read_text(encoding="utf-8"), "logs/shard-a.log\n")
        self.assertEqual(trace["child_thread_ids"], ["worker"])
        self.assertEqual(trace["usage_by_thread"]["parent"]["totalTokens"], 10)
        self.assertEqual(trace["usage_by_thread"]["worker"]["totalTokens"], 10)
        self.assertTrue(trace["forced_handoff_written"])
        self.assertTrue(trace["forced_handoff_consumed"])
        self.assertEqual(trace["spawn_records"]["worker"]["origin"], "harness_thread")

    def test_all_spawned_workers_must_be_useful(self) -> None:
        case = self.cases["incident-triage"]
        assignments = {"one": ["logs-ab", "logs-cd"], "two": ["logs-ef"]}
        messages = {
            "one": "logs/shard-a.log\nlogs/shard-c.log",
            "two": "no source provenance",
        }
        result = evaluate_delegation(
            case,
            ARM_SPECS["v8-spark-auto"],
            trace_for(case, assignments, messages=messages),
            "parent",
        )
        self.assertEqual(result["useful_worker_count"], 1)
        self.assertFalse(result["all_spawned_workers_useful"])
        self.assertFalse(result["routing_ok"])

    def test_running_or_unobserved_child_blocks_protocol(self) -> None:
        case = self.cases["incident-triage"]
        assignments = {"one": ["logs-ab", "logs-cd", "logs-ef"]}
        result = evaluate_delegation(
            case,
            ARM_SPECS["v8-spark-auto"],
            trace_for(case, assignments, statuses={"one": "running"}),
            "parent",
        )
        self.assertEqual(result["active_child_ids"], ["one"])
        self.assertFalse(result["no_active_children"])
        self.assertFalse(result["child_completion_ok"])
        self.assertFalse(result["routing_ok"])

    def test_no_spark_is_quiescent_and_uses_zero_workers(self) -> None:
        case = self.cases["incident-triage"]
        result = evaluate_delegation(
            case,
            ARM_SPECS["v8-no-spark"],
            trace_for(case, {}),
            "parent",
        )
        self.assertEqual(result["actual_spawned_workers"], 0)
        self.assertTrue(result["all_spawned_workers_useful"])
        self.assertTrue(result["no_active_children"])
        self.assertTrue(result["routing_ok"], result)

    def forced_trace(self, case: dict) -> dict:
        trace = trace_for(
            case,
            {"forced": [partition["id"] for partition in case["delegation"]["expected_partitions"]]},
        )
        agent = benchmark_v8.load_frozen_spark_agent()
        trace["spawn_records"]["forced"].update(
            {
                "origin": "harness_thread",
                "native_agent_role": False,
                "role": "spark_worker",
                "agent_sha256": hashlib.sha256(
                    benchmark_v8.SPARK_AGENT.read_bytes()
                ).hexdigest(),
                "instructions_sha256": hashlib.sha256(
                    agent["developer_instructions"].encode("utf-8")
                ).hexdigest(),
                "config_sha256": "frozen-config",
            }
        )
        trace["forced_handoff_written"] = True
        trace["forced_handoff_consumed"] = True
        return trace

    def test_forced_route_requires_exact_harness_identity(self) -> None:
        case = self.cases["incident-triage"]
        result = evaluate_delegation(
            case,
            ARM_SPECS["v8-spark-forced"],
            self.forced_trace(case),
            "parent",
        )
        self.assertTrue(result["spark_model_ok"])
        self.assertTrue(result["spawn_origin_ok"])
        self.assertTrue(result["role_binding_ok"])
        self.assertTrue(result["forced_handoff_ok"])
        self.assertTrue(result["routing_ok"], result)

    def test_wrong_forced_model_is_rejected_before_inference(self) -> None:
        case = self.cases["incident-triage"]
        trace = self.forced_trace(case)
        trace["spawn_records"]["forced"]["model"] = "gpt-5.6-luna"
        result = evaluate_delegation(
            case,
            ARM_SPECS["v8-spark-forced"],
            trace,
            "parent",
        )
        self.assertFalse(result["spark_model_ok"])
        self.assertFalse(result["routing_ok"])

    def test_forced_worker_write_to_parent_report_fails_routing(self) -> None:
        case = self.cases["monorepo-sdk-migration"]
        trace = self.forced_trace(case)
        trace["file_changes_by_thread"]["forced"] = ["migration_report.json"]
        result = evaluate_delegation(
            case,
            ARM_SPECS["v8-spark-forced"],
            trace,
            "parent",
        )
        self.assertFalse(result["worker_io_ok"])
        self.assertFalse(result["routing_ok"])


class PublicationGateTests(unittest.TestCase):
    @staticmethod
    def row(*, task: bool = True, protocol: bool = True, usage: bool = True) -> dict:
        return {
            "case_id": "case",
            "trial": 1,
            "arm": "v8-no-spark",
            "success": task and protocol,
            "task_pass": task,
            "protocol_pass": protocol,
            "grade": {
                "ok": task,
                "passed": 1 if task else 0,
                "total": 1,
                "score_pct": 100.0 if task else 0.0,
            },
            "usage_complete": usage,
            "all_spawned_workers_useful": True,
            "no_active_children": True,
        }

    def status(self, row: dict) -> dict:
        expected = expected_result_keys([{"id": "case"}], 1, ["v8-no-spark"])
        return publication_status([row], expected, repetitions=1, jobs=1)

    def test_single_pass_green_is_exploratory_not_repeat_confirmed(self) -> None:
        status = self.status(self.row())
        self.assertTrue(status["candidate_all_pass"])
        self.assertTrue(status["exploratory_metrics_publishable"])
        self.assertFalse(status["repeat_confirmed"])
        self.assertFalse(status["token_publishable"])

    def test_publication_rejects_any_task_failure(self) -> None:
        status = self.status(self.row(task=False))
        self.assertFalse(status["task_publishable"])
        self.assertFalse(status["candidate_all_pass"])
        self.assertFalse(status["exploratory_metrics_publishable"])

    def test_publication_rejects_any_protocol_failure(self) -> None:
        status = self.status(self.row(protocol=False))
        self.assertFalse(status["protocol_publishable"])
        self.assertFalse(status["candidate_all_pass"])
        self.assertFalse(status["exploratory_metrics_publishable"])

    def test_exploratory_metrics_require_complete_usage(self) -> None:
        status = self.status(self.row(usage=False))
        self.assertTrue(status["candidate_all_pass"])
        self.assertFalse(status["exploratory_metrics_publishable"])


class SparkEfficiencyMetricTests(unittest.TestCase):
    @staticmethod
    def row(arm: str, *, parent: int, combined: int, wall: float, workers: int) -> dict:
        return {
            "case_id": "case",
            "trial": 1,
            "arm": arm,
            "success": True,
            "grade": {"score_pct": 100.0},
            "parent_total_tokens": parent,
            "combined_total_tokens": combined,
            "execution_duration_seconds": wall,
            "actual_spawned_workers": workers,
            "useful_worker_count": workers,
        }

    def test_wall_time_fallback_is_reported_without_hiding_parent_regression(self) -> None:
        baseline = self.row(
            "v8-no-spark", parent=100, combined=100, wall=100.0, workers=0
        )
        candidate = self.row(
            "v8-spark-forced", parent=105, combined=300, wall=70.0, workers=2
        )
        comparison = comparison_rows(
            [baseline, candidate], ["v8-no-spark", "v8-spark-forced"]
        )[0]
        self.assertEqual(comparison["parent_tokens_saved"], -5)
        self.assertEqual(comparison["wall_seconds_saved"], 30.0)
        self.assertEqual(comparison["wall_seconds_saved_per_useful_worker"], 15.0)
        self.assertEqual(comparison["parent_allowance_winner"], "baseline")
        self.assertEqual(comparison["wall_time_winner"], "candidate")
        self.assertTrue(comparison["allowance_or_wall_time_win"])
        self.assertEqual(comparison["selection_winner"], "baseline")


if __name__ == "__main__":
    unittest.main()
