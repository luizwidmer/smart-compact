import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / "benchmarks" / "v8-freeze.json"


def git_blob_id(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode()
    return hashlib.sha1(header + data).hexdigest()


class V8FreezeTests(unittest.TestCase):
    def test_frozen_artifact_hashes_and_additive_plan_match(self) -> None:
        freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
        self.assertEqual(freeze["schema_version"], 2)
        self.assertEqual(freeze["primary_objective"], "parent_total_tokens")
        plan = freeze["release_plan"]
        self.assertEqual(plan["status"], "input_frozen")
        self.assertEqual(plan["seed"], 20260721)
        self.assertEqual(plan["repetitions_per_cell"], 1)
        self.assertEqual(plan["fresh_release_cells"], 66)
        self.assertEqual(plan["tuning_cells_outside_release"], 6)
        self.assertEqual(plan["total_evidence_cells"], 72)
        self.assertEqual(plan["case_universe"], 12)
        self.assertEqual(plan["official_legacy_live_cases"], 2)
        self.assertEqual(plan["newer_agentic_cases"], 10)
        self.assertEqual(plan["offline_guard_cases"], 7)
        self.assertEqual(
            plan["release_cell_allocation"],
            {
                "standard-no-spark": 12,
                "v6-no-spark": 12,
                "v8-no-spark": 21,
                "v8-spark-forced": 12,
                "v8-spark-auto": 9,
            },
        )
        self.assertEqual(
            plan["task_cell_allocation"],
            {
                "legacy-calculator": 16,
                "legacy-relay-bench": 16,
                "monorepo-sdk-migration": 16,
                "agentic-non-anchor": 18,
            },
        )
        self.assertEqual(plan["retained_release_selections"], 0)
        self.assertFalse(plan["latency_publishable"])

        for name, artifact in freeze["artifacts"].items():
            with self.subTest(name=name):
                data = (ROOT / artifact["path"]).read_bytes()
                self.assertEqual(hashlib.sha256(data).hexdigest(), artifact["sha256"])
                self.assertEqual(git_blob_id(data), artifact["git_blob"])


if __name__ == "__main__":
    unittest.main()
