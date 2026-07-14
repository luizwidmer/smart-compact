from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.benchmark_agentic import (
    BENCHMARK_RTK_INSTRUCTION,
    DEFAULT_CASES,
    INSTALLED_SKILL,
    apply_gold,
    arm_config,
    acceptance_command_observed,
    child_completion_ok,
    delegation_briefs_ok,
    evaluate_case,
    load_cases,
    paired_metrics,
    prepare_codex_home,
    prepare_workspace,
    run_case_trial,
    safe_relative_path,
    sort_results,
    usage_breakdown,
    validate_fixtures,
    write_json_payload,
)


class AgenticCaseTests(unittest.TestCase):
    def test_manifest_has_realistic_paired_coverage(self) -> None:
        cases = load_cases(DEFAULT_CASES)

        self.assertGreaterEqual(len(cases), 4)
        self.assertEqual(len({case["id"] for case in cases}), len(cases))
        self.assertEqual({case["split"] for case in cases}, {"development", "held-out"})
        self.assertTrue(any(case["offload_expected"] for case in cases))
        self.assertTrue(any(not case["offload_expected"] for case in cases))
        self.assertTrue(all(case["acceptance_command"] for case in cases))
        self.assertTrue(
            all(
                ("spark_worker" in case["prompt"]) == case["offload_expected"]
                for case in cases
            )
        )

    def test_fixture_oracles_pass_and_seeds_fail(self) -> None:
        result = validate_fixtures(load_cases(DEFAULT_CASES))

        self.assertTrue(result["ok"], result)
        for case in result["cases"]:
            self.assertLess(case["seed_score_pct"], 100.0)
            self.assertEqual(case["gold_score_pct"], 100.0)
            self.assertTrue(case["gold_scope_ok"])

    def test_fresh_workspaces_are_isolated(self) -> None:
        case = load_cases(DEFAULT_CASES)[0]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first_parent = root / "first"
            second_parent = root / "second"
            first_parent.mkdir()
            second_parent.mkdir()
            first = prepare_workspace(case, first_parent)
            second = prepare_workspace(case, second_parent)
            apply_gold(case, first)

            self.assertTrue(evaluate_case(case, first)["ok"])
            self.assertFalse(evaluate_case(case, second)["ok"])

    def test_fixture_paths_reject_escape(self) -> None:
        for value in ("../outside", "/absolute/path"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                safe_relative_path(value)


class AgenticRunnerTests(unittest.TestCase):
    def test_json_payload_writer_replaces_complete_document(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "nested" / "result.json"
            write_json_payload(path, {"complete": False})
            write_json_payload(path, {"complete": True})

            self.assertEqual(path.read_text(encoding="utf-8"), '{\n  "complete": true\n}\n')
            self.assertFalse(path.with_name(f".{path.name}.tmp").exists())

    def test_parallel_completion_order_is_normalized(self) -> None:
        rows = [
            {"case_id": "second", "trial": 1, "arm": "no-spark"},
            {"case_id": "first", "trial": 2, "arm": "spark"},
            {"case_id": "first", "trial": 1, "arm": "no-spark"},
            {"case_id": "first", "trial": 1, "arm": "spark"},
        ]

        ordered = sort_results(rows, ["first", "second"])

        self.assertEqual(
            [(row["case_id"], row["trial"], row["arm"]) for row in ordered],
            [
                ("first", 1, "spark"),
                ("first", 1, "no-spark"),
                ("first", 2, "spark"),
                ("second", 1, "no-spark"),
            ],
        )

    def test_pair_records_arm_errors_and_continues(self) -> None:
        case = load_cases(DEFAULT_CASES)[0]
        with tempfile.TemporaryDirectory() as temporary, mock.patch(
            "scripts.benchmark_agentic.prepare_workspace",
            side_effect=RuntimeError("synthetic failure"),
        ):
            rows = run_case_trial(
                case=case,
                trial=1,
                arm_order=["spark", "no-spark"],
                run_root=Path(temporary),
                codex="codex",
                profile={},
                model="parent",
                effort="high",
                response_timeout=1.0,
                turn_timeout=1.0,
                keep_workspaces=False,
            )

        self.assertEqual([row["arm"] for row in rows], ["spark", "no-spark"])
        self.assertTrue(all(row["turn_status"] == "runner_error" for row in rows))
        self.assertTrue(all("synthetic failure" in row["runner_error"] for row in rows))
        self.assertTrue(all(not row["success"] for row in rows))

    def test_isolated_codex_home_adds_agent_only_to_spark_arm(self) -> None:
        source = Path.home() / ".codex"
        if not (source / "auth.json").is_file() or not (
            source / "agents" / "spark-worker.toml"
        ).is_file():
            self.skipTest("installed Codex auth and Spark agent are required")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            spark = prepare_codex_home(root / "spark", spark_enabled=True)
            local = prepare_codex_home(root / "local", spark_enabled=False)

            self.assertTrue((spark / "auth.json").is_file())
            self.assertTrue((spark / "agents" / "spark-worker.toml").is_file())
            self.assertTrue((local / "auth.json").is_file())
            self.assertFalse((local / "agents").exists())

    def test_arm_toggle_is_the_only_profile_difference(self) -> None:
        profile = {
            "model_verbosity": "low",
            "features": {"record_replay": True},
            "agents": {"interrupt_message": False},
        }
        original = copy.deepcopy(profile)

        spark = arm_config(profile, "spark")
        local = arm_config(profile, "no-spark")

        self.assertEqual(profile, original)
        self.assertEqual(spark.pop("project_doc_max_bytes"), 0)
        self.assertEqual(local.pop("project_doc_max_bytes"), 0)
        self.assertTrue(spark["features"].pop("multi_agent"))
        self.assertFalse(local["features"].pop("multi_agent"))
        self.assertEqual(spark, local)
        self.assertIn(BENCHMARK_RTK_INSTRUCTION, spark["developer_instructions"])
        self.assertIn(
            {"path": str(INSTALLED_SKILL), "enabled": False},
            spark["skills"]["config"],
        )

    def test_usage_breakdown_fails_closed(self) -> None:
        usage = {
            "inputTokens": 10,
            "cachedInputTokens": 4,
            "outputTokens": 3,
            "reasoningOutputTokens": 2,
            "totalTokens": 13,
        }

        self.assertEqual(usage_breakdown(usage), usage)
        self.assertIsNone(usage_breakdown({"totalTokens": 15}))
        self.assertIsNone(usage_breakdown({**usage, "totalTokens": 99}))
        self.assertIsNone(usage_breakdown({**usage, "cachedInputTokens": 11}))
        self.assertIsNone(usage_breakdown(None))

    def test_expected_child_must_complete(self) -> None:
        statuses = {"child": "completed"}

        self.assertTrue(child_completion_ok(statuses, ["child"], 1))
        self.assertFalse(child_completion_ok({"child": "failed"}, ["child"], 1))
        self.assertTrue(child_completion_ok({}, [], 0))

    def test_delegation_brief_audit_fails_closed(self) -> None:
        compliant = (
            "The inherited working directory is already the target root; never run cd. "
            "Benchmark constraint: every shell command must start with literal `rtk`."
        )
        paraphrase = (
            "The inherited cwd is already the target root; shell cd/chdir is forbidden. "
            "Every command string's first word must be literal `rtk`."
        )

        self.assertTrue(delegation_briefs_ok([], 0))
        self.assertFalse(delegation_briefs_ok([compliant], 0))
        self.assertTrue(delegation_briefs_ok([compliant], 1))
        self.assertTrue(delegation_briefs_ok([paraphrase], 1))
        self.assertFalse(delegation_briefs_ok(["use rtk"], 1))
        self.assertFalse(
            delegation_briefs_ok(
                ["Every shell command must start with literal rtk."], 1
            )
        )
        self.assertFalse(delegation_briefs_ok([], 1))

    def test_acceptance_command_must_appear_in_parent_trace(self) -> None:
        acceptance = ["python3", "-m", "unittest", "discover", "-s", "tests", "-v"]
        commands = ["/bin/zsh -lc 'rtk proxy python3 -m unittest discover -s tests -v'"]

        self.assertTrue(acceptance_command_observed(commands, acceptance))
        self.assertFalse(acceptance_command_observed(["rtk git status --short"], acceptance))

    def test_paired_metrics_keep_parent_and_combined_tokens_separate(self) -> None:
        common = {
            "case_id": "case",
            "trial": 1,
            "usage_complete": True,
            "grade": {"ok": True, "score_pct": 100.0},
            "success": True,
        }
        spark = {
            **common,
            "arm": "spark",
            "parent_total_tokens": 60,
            "combined_total_tokens": 120,
            "duration_seconds": 5.0,
        }
        local = {
            **common,
            "arm": "no-spark",
            "parent_total_tokens": 100,
            "combined_total_tokens": 100,
            "duration_seconds": 10.0,
        }

        pair = paired_metrics([spark, local])[0]

        self.assertTrue(pair["valid"])
        self.assertEqual(pair["parent_token_reduction_pct"], 40.0)
        self.assertEqual(pair["combined_token_overhead_pct"], 20.0)
        self.assertEqual(pair["wall_time_reduction_pct"], 50.0)

        failed = {**spark, "success": False}
        self.assertFalse(paired_metrics([failed, local])[0]["valid"])


if __name__ == "__main__":
    unittest.main()
