from __future__ import annotations

import hashlib
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import benchmark_v9_official as official
from scripts import benchmark_v9_official_recovery as recovery
from scripts import verify_v9_official_recovery as verifier


def valid_recovery(parent_tokens: int = 50_000) -> dict:
    original = recovery.load_object(recovery.DEFAULT_ORIGINAL)
    cells = recovery.collision_cells(
        original,
        official.build_matrix(official.load_official_cases()),
    )
    order = recovery.execution_order_rows(original, cells)
    indexes = {row["cell_id"]: row["index"] for row in order}
    rows = []
    for cell in cells:
        spark = cell.arm == official.final.V9_SELECTED_SPARK_ARM
        child_id = f"child-{cell.effort}" if spark else None
        child_tokens = 100 if spark else 0
        rows.append(
            {
                "cell_id": cell.cell_id,
                "case_id": cell.case_id,
                "task_shape": cell.task_shape,
                "arm": cell.arm,
                "model": cell.model,
                "effort": cell.effort,
                "trial": 1,
                "execution_order_index": indexes[cell.cell_id],
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
    return {
        "schema_version": 1,
        "benchmark": "smart-compact-v9-official-recovery",
        "complete": True,
        "original_raw_path": str(verifier.DEFAULT_ORIGINAL.resolve()),
        "original_raw_sha256": hashlib.sha256(verifier.DEFAULT_ORIGINAL.read_bytes()).hexdigest(),
        "original_freeze_path": str(verifier.DEFAULT_ORIGINAL_FREEZE.resolve()),
        "original_freeze_sha256": hashlib.sha256(verifier.DEFAULT_ORIGINAL_FREEZE.read_bytes()).hexdigest(),
        "recovery_freeze_path": str(verifier.DEFAULT_RECOVERY_FREEZE.resolve()),
        "recovery_freeze_sha256": hashlib.sha256(verifier.DEFAULT_RECOVERY_FREEZE.read_bytes()).hexdigest(),
        "physical_cells": 9,
        "repetitions_per_cell": 1,
        "matrix": official.matrix_rows(cells),
        "execution_order": order,
        "seed": official.SEED,
        "jobs": 4,
        "wall_time_contended": True,
        "functional_task_passes": 9,
        "task_gate_passes": 9,
        "runner_cleanup": "per-cell app-server processes closed by context manager",
        "runner_status": "recovery_matrix_complete_not_release_verdict",
        "protocol_misses": [],
        "results": rows,
    }


class RecoveryVerifierTests(unittest.TestCase):
    def verify(self, payload: dict) -> dict:
        with tempfile.TemporaryDirectory() as temporary:
            freeze = json.loads(
                verifier.DEFAULT_RECOVERY_FREEZE.read_text(encoding="utf-8")
            )
            freeze["artifacts"]["optimizer_selection"]["path"] = (
                "benchmarks/experiments/v9-official-state-routed-rejected/"
                "artifacts/optimizer/selection.json"
            )
            freeze_path = Path(temporary) / "recovery-freeze.json"
            freeze_path.write_text(json.dumps(freeze), encoding="utf-8")
            payload = copy.deepcopy(payload)
            payload["recovery_freeze_path"] = str(freeze_path.resolve())
            payload["recovery_freeze_sha256"] = hashlib.sha256(
                freeze_path.read_bytes()
            ).hexdigest()
            path = Path(temporary) / "recovery.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            original = json.loads(
                verifier.DEFAULT_ORIGINAL.read_text(encoding="utf-8")
            )
            original["freeze_path"] = str(
                verifier.DEFAULT_ORIGINAL_FREEZE.resolve()
            )
            original_load = verifier.load

            def relocated_load(candidate: Path, label: str) -> dict:
                if candidate.resolve() == verifier.DEFAULT_ORIGINAL.resolve():
                    return copy.deepcopy(original)
                return original_load(candidate, label)

            with mock.patch.object(verifier, "load", side_effect=relocated_load):
                return verifier.verify(
                    recovery_path=path,
                    recovery_freeze_path=freeze_path,
                )

    def test_valid_recovery_yields_twelve_unique_real_cells(self) -> None:
        report = self.verify(valid_recovery())
        self.assertEqual(report["status"], "v9_official_retirement_gate_passed")
        self.assertEqual(report["original_real_inference_cells"], 3)
        self.assertEqual(report["recovery_real_inference_cells"], 9)
        self.assertEqual(report["repeated_real_inference_cells"], 0)
        self.assertEqual(report["effective_unique_cells"], 12)
        self.assertEqual(report["task_correct_cells"], 12)

    def test_recovery_cannot_repeat_a_valid_original_cell(self) -> None:
        payload = valid_recovery()
        payload["results"][0]["cell_id"] = next(
            row["cell_id"]
            for row in recovery.load_object(recovery.DEFAULT_ORIGINAL)["results"]
            if row.get("functional_task_pass") is True
        )
        with self.assertRaises(verifier.VerificationError):
            self.verify(payload)

    def test_recovery_must_beat_all_whole_versions_in_aggregate(self) -> None:
        with self.assertRaisesRegex(verifier.VerificationError, "does not beat every deployable"):
            self.verify(valid_recovery(parent_tokens=500_000))


if __name__ == "__main__":
    unittest.main()
