from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

import scripts.benchmark_v9 as benchmark_v9


ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / "benchmarks" / "v9-freeze.json"
REJECTED_ARCHIVE = (
    ROOT / "benchmarks" / "experiments" / "v9-state-minimal-rejected" / "artifacts"
)
ARCHIVED_PATHS = {
    "profiles/smart-compact-v9.config.toml": REJECTED_ARCHIVE
    / "profiles"
    / "smart-compact-v9.config.toml",
    "versions/v9/SKILL.md": REJECTED_ARCHIVE / "versions" / "v9" / "SKILL.md",
    "optimizer/selection.json": REJECTED_ARCHIVE / "optimizer" / "selection.json",
    "scripts/verify_v9_release.py": REJECTED_ARCHIVE
    / "scripts"
    / "verify_v9_release.py",
}


def frozen_artifact_path(path: str) -> Path:
    return ARCHIVED_PATHS.get(path, ROOT / path)


def git_blob_id(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode()
    return hashlib.sha1(header + data).hexdigest()


class V9ReleaseFreezeTests(unittest.TestCase):
    def test_rejected_freeze_is_preserved_byte_for_byte(self) -> None:
        archived = (
            ROOT
            / "benchmarks"
            / "experiments"
            / "v9-state-minimal-rejected"
            / "freeze.json"
        )
        self.assertEqual(FREEZE.read_bytes(), archived.read_bytes())

    def test_release_plan_is_frozen_before_inference(self) -> None:
        freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
        self.assertEqual(freeze["schema_version"], 1)
        self.assertEqual(freeze["candidate"], "v9")
        self.assertEqual(
            freeze["status"],
            "release_gate_inputs_frozen_before_inference",
        )
        self.assertEqual(freeze["primary_objective"], "parent_total_tokens")
        plan = freeze["release_plan"]
        self.assertEqual(plan["seed"], 20260715)
        self.assertEqual(plan["repetitions_per_cell"], 1)
        self.assertEqual(plan["jobs"], 4)
        self.assertEqual(plan["physical_cells"], 15)
        self.assertEqual(plan["logical_product_cells"], 16)
        self.assertEqual(plan["case_universe"], 4)
        self.assertEqual(plan["matrix"], benchmark_v9.matrix_rows())
        self.assertEqual(
            plan["release_cell_allocation"],
            {
                "v6-no-spark": 4,
                "v8-no-spark": 4,
                "v9-spark-auto": 4,
                "v9-natural-no-spark": 3,
            },
        )
        self.assertEqual(
            plan["wall_time_policy"],
            "diagnostic_only_contended_parallel_run",
        )
        self.assertEqual(
            plan["implementation_reuse_binding"],
            benchmark_v9.IMPLEMENTATION_REUSE_BINDING,
        )
        self.assertEqual(
            freeze["release_evidence"],
            {
                "status": "outputs_excluded_from_input_freeze",
                "raw_artifacts": [],
                "verified_cells": 0,
            },
        )

    def test_every_frozen_artifact_hash_and_git_blob_matches(self) -> None:
        freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(freeze["artifacts"]), 13)
        for name, artifact in freeze["artifacts"].items():
            with self.subTest(artifact=name):
                data = frozen_artifact_path(artifact["path"]).read_bytes()
                self.assertEqual(hashlib.sha256(data).hexdigest(), artifact["sha256"])
                self.assertEqual(git_blob_id(data), artifact["git_blob"])

    def test_implementation_reuse_is_byte_identical_not_inferred(self) -> None:
        freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
        artifacts = freeze["artifacts"]
        v6 = (ROOT / artifacts["v6_profile"]["path"]).read_bytes()
        implementation = frozen_artifact_path(
            artifacts["v9_implementation_profile"]["path"]
        ).read_bytes()
        self.assertEqual(v6, implementation)
        self.assertEqual(
            artifacts["v6_profile"]["sha256"],
            artifacts["v9_implementation_profile"]["sha256"],
        )
        binding = freeze["release_plan"]["implementation_reuse_binding"]
        self.assertEqual(binding["equivalence"], "byte_identical_profile")
        self.assertEqual(binding["additional_inference_cells"], 0)

    def test_first_three_cases_require_auto_and_general_forbids_it(self) -> None:
        payload = json.loads(benchmark_v9.DEFAULT_CASES.read_text(encoding="utf-8"))
        modes = {
            case["id"]: case["delegation"]["mode"] for case in payload["cases"]
        }
        self.assertEqual(
            modes,
            {
                "polyglot-record-normalizer": "required_when_available",
                "workspace-permission-migration": "required_when_available",
                "incident-window-correlation": "required_when_available",
                "ordered-entitlement-ledger": "forbidden",
            },
        )
        for case in payload["cases"][:3]:
            self.assertIsNone(case["delegation"]["spawned_workers"]["max"])
        general = payload["cases"][3]["delegation"]
        self.assertEqual(general["spawned_workers"], {"min": 0, "max": 0})
        self.assertEqual(general["expected_partitions"], [])


if __name__ == "__main__":
    unittest.main()
