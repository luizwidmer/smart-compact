from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts import benchmark_v9_official as benchmark
from scripts import verify_v9_official as verifier


def valid_raw(parent_tokens: int = 50_000) -> dict:
    cells = benchmark.build_matrix(benchmark.load_official_cases())
    order = benchmark.execution_order_rows(cells)
    order_index = {row["cell_id"]: row["index"] for row in order}
    results = []
    for cell in cells:
        spark = cell.arm == benchmark.final.V9_SELECTED_SPARK_ARM
        child_id = f"child-{cell.case_id}-{cell.effort}" if spark else None
        child_tokens = 100 if spark else 0
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
                "functional_task_pass": True,
                "task_gate_pass": True,
                "protocol_pass": True,
                "grade": {"ok": True, "score_pct": 100.0},
                "acceptance_observed": True,
                "scope_ok": True,
                "usage_complete": True,
                "rtk_ok": True,
                "no_active_children": True,
                "parent_total_tokens": parent_tokens,
                "child_total_tokens": child_tokens,
                "combined_total_tokens": parent_tokens + child_tokens,
                "actual_spawned_workers": 1 if spark else 0,
                "useful_worker_count": 1 if spark else 0,
                "execution_duration_seconds": 10.0,
                "child_thread_ids": [child_id] if child_id else [],
                "child_read_errors": {},
            }
        )
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
        for case_id in benchmark.CASE_SOURCES
    ]
    return {
        "schema_version": 1,
        "benchmark": "smart-compact-v9-official-completion",
        "complete": True,
        "case_sources": benchmark.source_rows(),
        "control_summary_path": str(benchmark.CONTROL_SUMMARY.resolve()),
        "control_summary_sha256": hashlib.sha256(benchmark.CONTROL_SUMMARY.read_bytes()).hexdigest(),
        "freeze_path": str(verifier.DEFAULT_FREEZE.resolve()),
        "freeze_sha256": hashlib.sha256(verifier.DEFAULT_FREEZE.read_bytes()).hexdigest(),
        "physical_cells": 12,
        "repetitions_per_cell": 1,
        "matrix": benchmark.matrix_rows(cells),
        "treatment": benchmark.OFFICIAL_TREATMENT,
        "seed": benchmark.SEED,
        "jobs": 4,
        "wall_time_contended": True,
        "execution_order": order,
        "fixture_validation": {"ok": True, "cases": fixture_rows},
        "functional_task_passes": 12,
        "task_gate_passes": 12,
        "runner_cleanup": "per-cell app-server processes closed by context manager",
        "runner_status": "matrix_complete_not_release_verdict",
        "protocol_misses": [],
        "results": results,
    }


class OfficialVerifierTests(unittest.TestCase):
    def verify(self, payload: dict) -> dict:
        with tempfile.TemporaryDirectory() as temporary:
            freeze = json.loads(verifier.DEFAULT_FREEZE.read_text(encoding="utf-8"))
            freeze["artifacts"]["optimizer_selection"]["path"] = (
                "benchmarks/experiments/v9-official-state-routed-rejected/"
                "artifacts/optimizer/selection.json"
            )
            freeze_path = Path(temporary) / "freeze.json"
            freeze_path.write_text(json.dumps(freeze), encoding="utf-8")
            payload = copy.deepcopy(payload)
            payload["freeze_path"] = str(freeze_path.resolve())
            payload["freeze_sha256"] = hashlib.sha256(freeze_path.read_bytes()).hexdigest()
            raw = Path(temporary) / "raw.json"
            raw.write_text(json.dumps(payload), encoding="utf-8")
            return verifier.verify_release(raw, freeze_path=freeze_path)

    def test_valid_release_beats_all_deployable_versions(self) -> None:
        report = self.verify(valid_raw())
        self.assertEqual(report["status"], "v9_official_retirement_gate_passed")
        self.assertEqual(report["task_correct_cells"], 12)
        self.assertEqual(report["totals"]["v9_parent_tokens"], 600_000)
        self.assertEqual(report["totals"]["standard_parent_tokens"], 3_138_482)
        self.assertEqual(report["totals"]["v6_parent_tokens"], 3_361_104)
        self.assertEqual(report["totals"]["v8_parent_tokens"], 3_004_930)
        self.assertEqual(report["totals"]["rowwise_prior_oracle_parent_tokens"], 2_472_665)
        self.assertEqual(report["totals"]["v9_spawned_workers"], 4)

    def test_local_spawn_is_a_hard_failure(self) -> None:
        payload = valid_raw()
        row = next(row for row in payload["results"] if row["arm"] == benchmark.final.V9_SELECTED_LOCAL_ARM)
        row["actual_spawned_workers"] = 1
        row["child_thread_ids"] = ["child-local"]
        with self.assertRaises(verifier.VerificationError):
            self.verify(payload)

    def test_task_correctness_is_a_hard_failure(self) -> None:
        payload = valid_raw()
        payload["results"][0]["task_pass"] = False
        payload["results"][0]["functional_task_pass"] = False
        payload["functional_task_passes"] = 11
        with self.assertRaises(verifier.VerificationError):
            self.verify(payload)

    def test_known_ephemeral_completion_miss_is_nonblocking(self) -> None:
        payload = valid_raw()
        row = next(row for row in payload["results"] if row["arm"] == benchmark.final.V9_SELECTED_SPARK_ARM)
        row["no_active_children"] = False
        row["task_gate_pass"] = False
        row["protocol_pass"] = False
        row["child_read_errors"] = {
            row["child_thread_ids"][0]: "thread/read failed: ephemeral threads do not support includeTurns"
        }
        payload["task_gate_passes"] = 11
        payload["protocol_misses"] = [row["cell_id"]]
        report = self.verify(payload)
        self.assertEqual(
            report["ephemeral_child_completion_telemetry_misses_nonblocking"],
            [row["cell_id"]],
        )

    def test_unexplained_active_child_is_rejected(self) -> None:
        payload = valid_raw()
        row = next(row for row in payload["results"] if row["arm"] == benchmark.final.V9_SELECTED_SPARK_ARM)
        row["no_active_children"] = False
        row["child_read_errors"] = {row["child_thread_ids"][0]: "unknown failure"}
        with self.assertRaises(verifier.VerificationError):
            self.verify(payload)

    def test_incomplete_or_duplicate_matrix_is_rejected(self) -> None:
        for mutation in ("missing", "duplicate"):
            payload = valid_raw()
            if mutation == "missing":
                payload["results"].pop()
            else:
                payload["results"][-1] = copy.deepcopy(payload["results"][0])
            with self.subTest(mutation=mutation), self.assertRaises(verifier.VerificationError):
                self.verify(payload)

    def test_retirement_gate_requires_aggregate_win(self) -> None:
        payload = valid_raw(parent_tokens=300_000)
        with self.assertRaisesRegex(verifier.VerificationError, "does not beat every deployable"):
            self.verify(payload)


if __name__ == "__main__":
    unittest.main()
