from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import scripts.benchmark_v9 as benchmark_v9
import scripts.verify_v9_release as verifier


def valid_raw(freeze_path: Path = verifier.DEFAULT_FREEZE) -> dict:
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    artifacts = freeze["artifacts"]
    arm_metadata = {
        benchmark_v9.V6_ARM: {
            "spark_enabled": False,
            "multi_agent": False,
            "routing_mode": "none",
            "profile_sha256": artifacts["v6_profile"]["sha256"],
            "policy_sha256": artifacts["v6_policy"]["sha256"],
            "skill_input": True,
        },
        benchmark_v9.V8_ARM: {
            "spark_enabled": False,
            "multi_agent": False,
            "routing_mode": "none",
            "profile_sha256": artifacts["v8_profile"]["sha256"],
            "policy_sha256": artifacts["v8_policy"]["sha256"],
            "skill_input": False,
        },
        benchmark_v9.V9_NATURAL_ARM: {
            "spark_enabled": False,
            "multi_agent": False,
            "routing_mode": "none",
            "profile_sha256": artifacts["v9_natural_profile"]["sha256"],
            "policy_sha256": None,
            "skill_input": False,
        },
        benchmark_v9.V9_AUTO_ARM: {
            "spark_enabled": True,
            "multi_agent": True,
            "routing_mode": "auto",
            "profile_sha256": artifacts["v9_profile"]["sha256"],
            "policy_sha256": None,
            "skill_input": False,
        },
    }
    parent_tokens = {
        benchmark_v9.V6_ARM: 1000,
        benchmark_v9.V8_ARM: 1100,
        benchmark_v9.V9_NATURAL_ARM: 800,
        benchmark_v9.V9_AUTO_ARM: 700,
    }
    durations = {
        benchmark_v9.V6_ARM: 100.0,
        benchmark_v9.V8_ARM: 90.0,
        benchmark_v9.V9_NATURAL_ARM: 80.0,
        benchmark_v9.V9_AUTO_ARM: 70.0,
    }
    results = []
    for cell in benchmark_v9.MATRIX:
        required_auto = (
            cell.arm == benchmark_v9.V9_AUTO_ARM
            and cell.case_id != "ordered-entitlement-ledger"
        )
        child_id = f"child-{cell.case_id}" if required_auto else None
        child_tokens = 100 if required_auto else 0
        parent = parent_tokens[cell.arm]
        row = {
            "cell_id": cell.cell_id,
            "case_id": cell.case_id,
            "task_shape": cell.task_shape,
            "arm": cell.arm,
            "model": cell.model,
            "effort": cell.effort,
            "trial": 1,
            "task_pass": True,
            "task_gate_pass": True,
            "protocol_pass": True,
            "grade": {"ok": True, "score_pct": 100.0},
            "acceptance_observed": True,
            "scope_ok": True,
            "usage_complete": True,
            "rtk_ok": True,
            "no_active_children": True,
            "parent_total_tokens": parent,
            "child_total_tokens": child_tokens,
            "combined_total_tokens": parent + child_tokens,
            "actual_spawned_workers": 1 if required_auto else 0,
            "useful_worker_count": 1 if required_auto else 0,
            "execution_duration_seconds": durations[cell.arm],
            "routing_mode": "auto" if cell.arm == benchmark_v9.V9_AUTO_ARM else "none",
            "child_thread_ids": [child_id] if child_id else [],
            "child_roles": {child_id: "spark_worker"} if child_id else {},
            "spawn_records": (
                {
                    child_id: {
                        "model": "gpt-5.3-codex-spark",
                        "origin": "parent_agent",
                        "native_agent_role": True,
                    }
                }
                if child_id
                else {}
            ),
            "all_spawned_workers_useful": True,
            "role_ok": True,
            "spark_model_ok": True,
            "spawn_origin_ok": True,
            "role_binding_ok": True,
            "child_completion_ok": True,
        }
        results.append(row)
    fixture_rows = [
        {
            "case_id": case_id,
            "ok": True,
            "reset_reproducible": True,
            "seed_score_pct": 0.0,
            "gold_score_pct": 100.0,
            "gold_after_acceptance_score_pct": 100.0,
            "gold_acceptance_ok": True,
            "gold_scope_ok": True,
        }
        for case_id in (
            "polyglot-record-normalizer",
            "workspace-permission-migration",
            "incident-window-correlation",
            "ordered-entitlement-ledger",
        )
    ]
    return {
        "schema_version": 1,
        "benchmark": "smart-compact-v9-heldout-release",
        "complete": True,
        "physical_cells": 15,
        "logical_product_cells": 16,
        "repetitions_per_cell": 1,
        "jobs": 4,
        "wall_time_contended": True,
        "seed": 20260715,
        "matrix": benchmark_v9.matrix_rows(),
        "freeze_sha256": hashlib.sha256(freeze_path.read_bytes()).hexdigest(),
        "cases_sha256": artifacts["heldout_cases"]["sha256"],
        "treatment": {
            "v9_auto_availability_prompt_injected": False,
            "v9_auto_multi_agent_config": True,
            "forced_spark_included": False,
            "fixed_worker_cap": None,
        },
        "arm_metadata": arm_metadata,
        "implementation_reuse_binding": {
            **benchmark_v9.IMPLEMENTATION_REUSE_BINDING,
            "v6_sha256": artifacts["v6_profile"]["sha256"],
            "v9_implementation_sha256": artifacts["v9_implementation_profile"]["sha256"],
        },
        "fixture_validation": {"ok": True, "cases": fixture_rows},
        "task_gate_passes": 15,
        "protocol_misses": [],
        "results": results,
    }


class V9ReleaseVerifierTests(unittest.TestCase):
    def verify(self, payload: dict) -> dict:
        with tempfile.TemporaryDirectory() as temporary:
            raw = Path(temporary) / "raw.json"
            raw.write_text(json.dumps(payload), encoding="utf-8")
            return verifier.verify_release(raw)

    def test_valid_release_passes_and_reports_worker_efficiency(self) -> None:
        report = self.verify(valid_raw())
        self.assertEqual(report["status"], "v9_release_gate_passed")
        self.assertEqual(report["physical_cells_verified"], 15)
        self.assertEqual(report["logical_product_cells_verified"], 16)
        self.assertTrue(report["implementation_result_reused"])
        self.assertEqual(report["implementation_additional_inference_cells"], 0)
        self.assertIsNone(report["worker_cap"])
        self.assertFalse(report["wall_time_publishable"])
        self.assertEqual(report["totals"]["v6_parent_tokens"], 4000)
        self.assertEqual(report["totals"]["v8_parent_tokens"], 4400)
        self.assertEqual(report["totals"]["selected_v9_parent_tokens"], 3400)
        self.assertEqual(report["totals"]["v9_auto_parent_tokens"], 2800)
        self.assertEqual(report["totals"]["v9_auto_spawned_workers"], 3)
        self.assertEqual(
            report["totals"]["v9_auto_parent_tokens_saved_per_spawned_worker"],
            400.0,
        )

    def test_protocol_only_miss_is_disclosed_but_nonblocking(self) -> None:
        payload = valid_raw()
        row = payload["results"][0]
        row["protocol_pass"] = False
        payload["protocol_misses"] = [row["cell_id"]]
        report = self.verify(payload)
        self.assertEqual(report["protocol_misses_nonblocking"], [row["cell_id"]])

    def test_missing_duplicate_or_wrong_setting_cell_fails(self) -> None:
        mutations = []
        missing = valid_raw()
        missing["results"].pop()
        mutations.append(missing)
        duplicate = valid_raw()
        duplicate["results"][-1] = copy.deepcopy(duplicate["results"][0])
        mutations.append(duplicate)
        wrong_setting = valid_raw()
        wrong_setting["results"][0]["effort"] = "high"
        mutations.append(wrong_setting)
        for payload in mutations:
            with self.subTest(), self.assertRaises(verifier.VerificationError):
                self.verify(payload)

    def test_correctness_acceptance_scope_usage_and_rtk_are_hard_gates(self) -> None:
        for key in (
            "task_pass",
            "acceptance_observed",
            "scope_ok",
            "usage_complete",
            "rtk_ok",
            "no_active_children",
            "task_gate_pass",
        ):
            payload = valid_raw()
            payload["results"][0][key] = False
            with self.subTest(key=key), self.assertRaises(verifier.VerificationError):
                self.verify(payload)

    def test_no_spark_worker_or_child_tokens_fail(self) -> None:
        for field, value in (
            ("actual_spawned_workers", 1),
            ("useful_worker_count", 1),
            ("child_total_tokens", 1),
        ):
            payload = valid_raw()
            row = payload["results"][0]
            row[field] = value
            if field == "child_total_tokens":
                row["combined_total_tokens"] += 1
            with self.subTest(field=field), self.assertRaises(verifier.VerificationError):
                self.verify(payload)

    def test_required_auto_role_model_origin_usefulness_and_drain_are_hard(self) -> None:
        field_mutations = {
            "actual_spawned_workers": 0,
            "useful_worker_count": 0,
            "all_spawned_workers_useful": False,
            "role_ok": False,
            "spark_model_ok": False,
            "spawn_origin_ok": False,
            "role_binding_ok": False,
            "child_completion_ok": False,
        }
        auto_index = 2
        for field, value in field_mutations.items():
            payload = valid_raw()
            payload["results"][auto_index][field] = value
            with self.subTest(field=field), self.assertRaises(verifier.VerificationError):
                self.verify(payload)

    def test_general_auto_must_stay_local(self) -> None:
        payload = valid_raw()
        row = next(
            row
            for row in payload["results"]
            if row["cell_id"]
            == "ordered-entitlement-ledger::v9-spark-auto"
        )
        row["actual_spawned_workers"] = 1
        row["useful_worker_count"] = 1
        with self.assertRaises(verifier.VerificationError):
            self.verify(payload)

    def test_auto_can_lose_one_dimension_but_not_parent_and_wall_together(self) -> None:
        payload = valid_raw()
        auto = payload["results"][2]
        auto["parent_total_tokens"] = 1050
        auto["combined_total_tokens"] = 1150
        auto["execution_duration_seconds"] = 80.0
        self.verify(payload)

        payload = valid_raw()
        auto = payload["results"][2]
        auto["parent_total_tokens"] = 1050
        auto["combined_total_tokens"] = 1150
        auto["execution_duration_seconds"] = 120.0
        with self.assertRaises(verifier.VerificationError):
            self.verify(payload)

    def test_selected_and_auto_aggregate_must_strictly_beat_both_controls(self) -> None:
        selected = valid_raw()
        for row in selected["results"]:
            if row["arm"] == benchmark_v9.V9_NATURAL_ARM:
                row["parent_total_tokens"] = 1000
                row["combined_total_tokens"] = 1000
        with self.assertRaises(verifier.VerificationError):
            self.verify(selected)

        auto = valid_raw()
        for row in auto["results"]:
            if row["arm"] == benchmark_v9.V9_AUTO_ARM:
                row["parent_total_tokens"] = 1000
                row["combined_total_tokens"] = 1100 if row["child_total_tokens"] else 1000
                row["execution_duration_seconds"] = 60.0
        with self.assertRaises(verifier.VerificationError):
            self.verify(auto)

    def test_prompt_injection_binding_and_parallel_disclosure_are_hard(self) -> None:
        mutations = []
        prompt = valid_raw()
        prompt["treatment"]["v9_auto_availability_prompt_injected"] = True
        mutations.append(prompt)
        binding = valid_raw()
        binding["implementation_reuse_binding"]["v9_implementation_sha256"] = "0" * 64
        mutations.append(binding)
        jobs = valid_raw()
        jobs["jobs"] = 1
        jobs["wall_time_contended"] = False
        mutations.append(jobs)
        for payload in mutations:
            with self.subTest(), self.assertRaises(verifier.VerificationError):
                self.verify(payload)


if __name__ == "__main__":
    unittest.main()
