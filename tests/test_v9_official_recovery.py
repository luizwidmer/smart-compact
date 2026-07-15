from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

from scripts import benchmark_v9_official as official
from scripts import benchmark_v9_official_recovery as recovery
from scripts.freeze_v9_official_recovery import ARTIFACTS, blob_id


ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / "benchmarks/v9-official-recovery-freeze.json"
ARCHIVED_PATHS = {
    "optimizer/selection.json": ROOT
    / "benchmarks"
    / "experiments"
    / "v9-official-state-routed-rejected"
    / "artifacts"
    / "optimizer"
    / "selection.json",
}


def artifact_path(relative: str) -> Path:
    return ARCHIVED_PATHS.get(relative, ROOT / relative)


class RecoveryPlanTests(unittest.TestCase):
    def setUp(self) -> None:
        self.original = recovery.load_object(recovery.DEFAULT_ORIGINAL)
        self.full = official.build_matrix(official.load_official_cases())
        self.cells = recovery.collision_cells(self.original, self.full)

    def test_only_nine_collision_non_attempts_are_recovered(self) -> None:
        recovery_ids = {cell.cell_id for cell in self.cells}
        valid_ids = {
            row["cell_id"]
            for row in self.original["results"]
            if row.get("functional_task_pass") is True
        }
        self.assertEqual(len(recovery_ids), 9)
        self.assertEqual(len(valid_ids), 3)
        self.assertFalse(recovery_ids & valid_ids)
        self.assertEqual(recovery_ids | valid_ids, {cell.cell_id for cell in self.full})

    def test_every_recovery_cell_has_a_unique_workspace_namespace(self) -> None:
        roots = [recovery.cell_run_root(ROOT / "run", cell) for cell in self.cells]
        self.assertEqual(len(roots), 9)
        self.assertEqual(len(set(roots)), 9)

    def test_filtered_order_is_deterministic_and_complete(self) -> None:
        order = recovery.execution_order_rows(self.original, self.cells)
        self.assertEqual(order, recovery.execution_order_rows(self.original, self.cells))
        self.assertEqual([row["index"] for row in order], list(range(9)))
        self.assertEqual({row["cell_id"] for row in order}, {cell.cell_id for cell in self.cells})

    def test_freeze_binds_every_input_and_excludes_outputs(self) -> None:
        freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
        self.assertEqual(freeze["candidate"], "v9-official-collision-recovery")
        self.assertEqual(freeze["status"], "recovery_inputs_frozen_before_inference")
        self.assertEqual(freeze["primary_objective"], "parent_total_tokens")
        self.assertEqual(freeze["release_plan"]["physical_cells"], 9)
        self.assertEqual(set(freeze["artifacts"]), set(ARTIFACTS))
        self.assertEqual(
            freeze["release_evidence"],
            {"status": "outputs_excluded_from_input_freeze", "raw_artifacts": [], "verified_cells": 0},
        )
        for name, artifact in freeze["artifacts"].items():
            with self.subTest(name=name):
                data = artifact_path(artifact["path"]).read_bytes()
                self.assertEqual(hashlib.sha256(data).hexdigest(), artifact["sha256"])
                self.assertEqual(blob_id(data), artifact["git_blob"])


if __name__ == "__main__":
    unittest.main()
