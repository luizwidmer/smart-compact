from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

from scripts import benchmark_v9_final as benchmark
from scripts.freeze_v9_final import ARTIFACTS, git_blob_id


ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / "benchmarks" / "v9-final-freeze.json"
ARCHIVED_PATHS = {
    "optimizer/selection.json": ROOT
    / "benchmarks"
    / "experiments"
    / "v9-final-rejected"
    / "artifacts"
    / "optimizer"
    / "selection.json",
}


def artifact_path(relative: str) -> Path:
    return ARCHIVED_PATHS.get(relative, ROOT / relative)


class V9FinalFreezeTests(unittest.TestCase):
    def test_release_inputs_are_frozen_before_inference(self) -> None:
        freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
        self.assertEqual(freeze["schema_version"], 1)
        self.assertEqual(freeze["candidate"], "v9-definitive")
        self.assertEqual(
            freeze["status"],
            "release_gate_inputs_frozen_before_inference",
        )
        self.assertEqual(freeze["primary_objective"], "parent_total_tokens")
        self.assertEqual(freeze["treatment"], benchmark.FINAL_TREATMENT)
        self.assertEqual(
            freeze["release_evidence"],
            {
                "status": "outputs_excluded_from_input_freeze",
                "raw_artifacts": [],
                "verified_cells": 0,
            },
        )

    def test_rejected_selection_input_is_archived_exactly(self) -> None:
        freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
        artifact = freeze["artifacts"]["optimizer_selection"]
        archived = artifact_path(artifact["path"])
        self.assertEqual(hashlib.sha256(archived.read_bytes()).hexdigest(), artifact["sha256"])

    def test_every_artifact_hash_and_git_blob_matches(self) -> None:
        freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
        self.assertEqual(set(freeze["artifacts"]), set(ARTIFACTS))
        for name, artifact in freeze["artifacts"].items():
            with self.subTest(name=name):
                data = artifact_path(artifact["path"]).read_bytes()
                self.assertEqual(hashlib.sha256(data).hexdigest(), artifact["sha256"])
                self.assertEqual(git_blob_id(data), artifact["git_blob"])

    def test_plan_is_one_pass_parallel_and_deterministic(self) -> None:
        freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
        plan = freeze["release_plan"]
        self.assertEqual(plan["seed"], benchmark.SEED)
        self.assertEqual(plan["repetitions_per_cell"], 1)
        self.assertEqual(plan["jobs"], 4)
        self.assertEqual(plan["physical_cells"], 14)
        matrix = benchmark.validate_matrix_rows(plan["matrix"])
        self.assertEqual(plan["execution_order"], benchmark.execution_order_rows(matrix))


if __name__ == "__main__":
    unittest.main()
