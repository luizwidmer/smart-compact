from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import scripts.benchmark_v9_final as benchmark
import scripts.verify_v9_final_release as verifier


def final_cases() -> list[dict]:
    return benchmark.benchmark_v8.load_cases(benchmark.DEFAULT_CASES)


def arm_metadata() -> dict:
    digest = "a" * 64
    return {
        benchmark.V6_ARM: {
            "spark_enabled": False,
            "multi_agent": False,
            "routing_mode": "none",
            "profile_path": str(benchmark.V6_PROFILE),
            "policy_path": str(benchmark.V6_POLICY),
            "skill_input": True,
            "profile_sha256": digest,
            "policy_sha256": digest,
        },
        benchmark.V8_ARM: {
            "spark_enabled": False,
            "multi_agent": False,
            "routing_mode": "none",
            "profile_path": str(benchmark.V8_PROFILE),
            "policy_path": str(benchmark.V8_POLICY),
            "skill_input": False,
            "profile_sha256": digest,
            "policy_sha256": digest,
        },
        benchmark.V9_SELECTED_SPARK_ARM: {
            "spark_enabled": True,
            "multi_agent": True,
            "routing_mode": "auto",
            "profile_path": str(benchmark.V9_SPARK_PROFILE),
            "policy_path": None,
            "skill_input": False,
            "profile_sha256": digest,
            "policy_sha256": None,
        },
        benchmark.V9_SELECTED_LOCAL_ARM: {
            "spark_enabled": False,
            "multi_agent": False,
            "routing_mode": "none",
            "profile_path": str(benchmark.V9_LOCAL_PROFILE),
            "policy_path": None,
            "skill_input": False,
            "profile_sha256": digest,
            "policy_sha256": None,
        },
        benchmark.V9_LOCAL_COUNTERFACTUAL_ARM: {
            "spark_enabled": False,
            "multi_agent": False,
            "routing_mode": "none",
            "profile_path": str(benchmark.V9_LOCAL_PROFILE),
            "policy_path": None,
            "skill_input": False,
            "profile_sha256": digest,
            "policy_sha256": None,
        },
    }


def valid_raw() -> dict:
    matrix = benchmark.build_matrix(final_cases())
    execution_order = benchmark.execution_order_rows(matrix)
    order_index = {row["cell_id"]: row["index"] for row in execution_order}
    parent_tokens = {
        benchmark.V6_ARM: 1000,
        benchmark.V8_ARM: 1100,
        benchmark.V9_SELECTED_SPARK_ARM: 700,
        benchmark.V9_SELECTED_LOCAL_ARM: 700,
        benchmark.V9_LOCAL_COUNTERFACTUAL_ARM: 800,
    }
    durations = {
        benchmark.V6_ARM: 100.0,
        benchmark.V8_ARM: 90.0,
        benchmark.V9_SELECTED_SPARK_ARM: 70.0,
        benchmark.V9_SELECTED_LOCAL_ARM: 80.0,
        benchmark.V9_LOCAL_COUNTERFACTUAL_ARM: 80.0,
    }
    results = []
    for cell in matrix:
        selected_spark = cell.arm == benchmark.V9_SELECTED_SPARK_ARM
        child_id = f"child-{cell.case_id}" if selected_spark else None
        child_tokens = 100 if selected_spark else 0
        parent = parent_tokens[cell.arm]
        results.append(
            {
                "cell_id": cell.cell_id,
                "case_id": cell.case_id,
                "task_shape": cell.task_shape,
                "arm": cell.arm,
                "model": cell.model,
                "effort": cell.effort,
                "trial": 1,
                "execution_order_index": order_index[cell.cell_id],
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
                "actual_spawned_workers": 1 if selected_spark else 0,
                "useful_worker_count": 1 if selected_spark else 0,
                "execution_duration_seconds": durations[cell.arm],
                "routing_mode": "auto" if selected_spark else "none",
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
        )
    fixture_rows = [
        {
            "case_id": case["id"],
            "ok": True,
            "reset_reproducible": True,
            "seed_score_pct": 0.0,
            "gold_score_pct": 100.0,
            "gold_after_acceptance_score_pct": 100.0,
            "gold_acceptance_ok": True,
            "gold_scope_ok": True,
        }
        for case in final_cases()
    ]
    return {
        "schema_version": 1,
        "benchmark": "smart-compact-v9-final-release",
        "complete": True,
        "physical_cells": 14,
        "repetitions_per_cell": 1,
        "jobs": 4,
        "wall_time_contended": True,
        "seed": benchmark.SEED,
        "cases_path": str(benchmark.DEFAULT_CASES.resolve()),
        "cases_sha256": hashlib.sha256(benchmark.DEFAULT_CASES.read_bytes()).hexdigest(),
        "freeze_path": str(verifier.DEFAULT_FREEZE.resolve()),
        "freeze_sha256": hashlib.sha256(verifier.DEFAULT_FREEZE.read_bytes()).hexdigest(),
        "matrix": benchmark.matrix_rows(matrix),
        "execution_order": execution_order,
        "treatment": {
            "availability_prompt_injected": False,
            "selected_spark_multi_agent_config": True,
            "selected_local_multi_agent_config": False,
            "fixed_worker_cap": None,
            "spark_shapes": sorted(benchmark.SPARK_SHAPES),
            "local_shapes": sorted(benchmark.LOCAL_SHAPES),
            "local_counterfactual_shapes": sorted(benchmark.SPARK_SHAPES),
        },
        "arm_metadata": arm_metadata(),
        "fixture_validation": {"ok": True, "cases": fixture_rows},
        "task_gate_passes": 14,
        "runner_status": "matrix_complete_not_release_verdict",
        "protocol_misses": [],
        "results": results,
    }


class FinalReleaseVerifierTests(unittest.TestCase):
    def verify(self, payload: dict) -> dict:
        with tempfile.TemporaryDirectory() as temporary:
            freeze = json.loads(verifier.DEFAULT_FREEZE.read_text(encoding="utf-8"))
            freeze["artifacts"]["optimizer_selection"]["path"] = (
                "benchmarks/experiments/v9-final-rejected/artifacts/optimizer/selection.json"
            )
            freeze_path = Path(temporary) / "freeze.json"
            freeze_path.write_text(json.dumps(freeze), encoding="utf-8")
            payload = copy.deepcopy(payload)
            payload["freeze_path"] = str(freeze_path.resolve())
            payload["freeze_sha256"] = hashlib.sha256(freeze_path.read_bytes()).hexdigest()
            raw = Path(temporary) / "raw.json"
            raw.write_text(json.dumps(payload), encoding="utf-8")
            return verifier.verify_release(raw, freeze_path=freeze_path)

    def selected_spark(self, payload: dict, shape: str = "implementation") -> dict:
        return next(
            row
            for row in payload["results"]
            if row["arm"] == benchmark.V9_SELECTED_SPARK_ARM
            and row["task_shape"] == shape
        )

    def test_valid_fourteen_cell_release_passes(self) -> None:
        report = self.verify(valid_raw())
        self.assertEqual(report["status"], "v9_final_release_gate_passed")
        self.assertEqual(report["physical_cells_verified"], 14)
        self.assertEqual(report["task_correct_cells"], 14)
        self.assertIsNone(report["worker_cap"])
        self.assertFalse(report["wall_time_publishable"])
        self.assertEqual(report["totals"]["v6_parent_tokens"], 4000)
        self.assertEqual(report["totals"]["v8_parent_tokens"], 4400)
        self.assertEqual(report["totals"]["selected_v9_parent_tokens"], 2800)
        self.assertEqual(report["totals"]["selected_v9_spawned_workers"], 2)
        self.assertEqual(
            report["totals"]["spark_offload_parent_tokens_saved_per_spawned_worker"],
            100.0,
        )

    def test_protocol_only_miss_is_disclosed_but_nonblocking(self) -> None:
        payload = valid_raw()
        row = payload["results"][0]
        row["protocol_pass"] = False
        payload["protocol_misses"] = [row["cell_id"]]
        report = self.verify(payload)
        self.assertEqual(report["protocol_misses_nonblocking"], [row["cell_id"]])

    def test_worker_usefulness_miss_is_protocol_only(self) -> None:
        payload = valid_raw()
        row = self.selected_spark(payload)
        row["useful_worker_count"] = 0
        row["all_spawned_workers_useful"] = False
        row["protocol_pass"] = False
        payload["protocol_misses"] = [row["cell_id"]]
        report = self.verify(payload)
        self.assertTrue(report["worker_usefulness_protocol_only"])

    def test_missing_duplicate_or_wrong_setting_cell_fails(self) -> None:
        mutations = []
        missing = valid_raw()
        missing["results"].pop()
        mutations.append(missing)
        duplicate = valid_raw()
        duplicate["results"][-1] = copy.deepcopy(duplicate["results"][0])
        mutations.append(duplicate)
        wrong_setting = valid_raw()
        wrong_setting["matrix"][0]["effort"] = "high"
        mutations.append(wrong_setting)
        for payload in mutations:
            with self.subTest(), self.assertRaises(verifier.VerificationError):
                self.verify(payload)

    def test_all_functional_task_gates_are_hard(self) -> None:
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

    def test_every_local_or_control_cell_requires_zero_workers_and_child_tokens(self) -> None:
        for field, value in (
            ("actual_spawned_workers", 1),
            ("useful_worker_count", 1),
            ("child_total_tokens", 1),
        ):
            payload = valid_raw()
            row = next(
                row
                for row in payload["results"]
                if row["arm"] == benchmark.V9_LOCAL_COUNTERFACTUAL_ARM
            )
            row[field] = value
            if field == "child_total_tokens":
                row["combined_total_tokens"] += 1
            with self.subTest(field=field), self.assertRaises(verifier.VerificationError):
                self.verify(payload)

    def test_selected_spark_requires_exact_native_drained_worker(self) -> None:
        scalar_mutations = {
            "actual_spawned_workers": 0,
            "role_ok": False,
            "spark_model_ok": False,
            "spawn_origin_ok": False,
            "role_binding_ok": False,
            "child_completion_ok": False,
            "no_active_children": False,
        }
        for field, value in scalar_mutations.items():
            payload = valid_raw()
            self.selected_spark(payload)[field] = value
            with self.subTest(field=field), self.assertRaises(verifier.VerificationError):
                self.verify(payload)

        payload = valid_raw()
        row = self.selected_spark(payload)
        child_id = row["child_thread_ids"][0]
        row["spawn_records"][child_id]["native_agent_role"] = False
        with self.assertRaises(verifier.VerificationError):
            self.verify(payload)

    def test_spark_must_strictly_reduce_parent_tokens_against_paired_local(self) -> None:
        payload = valid_raw()
        row = self.selected_spark(payload)
        row["execution_duration_seconds"] = 90.0
        self.verify(payload)

        payload = valid_raw()
        row = self.selected_spark(payload)
        row["parent_total_tokens"] = 800
        row["combined_total_tokens"] = 900
        row["execution_duration_seconds"] = 70.0
        with self.assertRaises(verifier.VerificationError):
            self.verify(payload)

    def test_selected_aggregate_must_strictly_beat_both_controls(self) -> None:
        payload = valid_raw()
        for row in payload["results"]:
            if row["arm"] in (
                benchmark.V9_SELECTED_SPARK_ARM,
                benchmark.V9_SELECTED_LOCAL_ARM,
            ):
                row["parent_total_tokens"] = 1100
                row["combined_total_tokens"] = 1200 if row["child_total_tokens"] else 1100
                row["execution_duration_seconds"] = 60.0
        with self.assertRaises(verifier.VerificationError):
            self.verify(payload)

    def test_prompt_injection_fixed_cap_and_parallelism_are_hard(self) -> None:
        mutations = []
        prompt = valid_raw()
        prompt["treatment"]["availability_prompt_injected"] = True
        mutations.append(prompt)
        cap = valid_raw()
        cap["treatment"]["fixed_worker_cap"] = 1
        mutations.append(cap)
        jobs = valid_raw()
        jobs["jobs"] = 1
        jobs["wall_time_contended"] = False
        mutations.append(jobs)
        for payload in mutations:
            with self.subTest(), self.assertRaises(verifier.VerificationError):
                self.verify(payload)


if __name__ == "__main__":
    unittest.main()
