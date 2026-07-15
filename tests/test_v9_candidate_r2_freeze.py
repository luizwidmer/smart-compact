from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
FREEZE = ROOT / "benchmarks" / "experiments" / "v9-candidate-r2" / "freeze.json"


class V9CandidateR2FreezeTests(unittest.TestCase):
    def test_frozen_artifact_hashes_match(self) -> None:
        payload = json.loads(FREEZE.read_text(encoding="utf-8"))
        self.assertEqual(payload["status"], "target_gate_input_frozen_before_inference")
        self.assertEqual(payload["target_gate"]["case_id"], "multi-service-contract-rollout")
        self.assertEqual(payload["target_gate"]["arms"], ["v8-no-spark", "v8-spark-auto"])
        self.assertEqual(payload["policy_static_score"]["tokens"], 381)
        for name, artifact in payload["artifacts"].items():
            with self.subTest(artifact=name):
                path = ROOT / artifact["path"]
                self.assertTrue(path.is_file())
                self.assertEqual(
                    hashlib.sha256(path.read_bytes()).hexdigest(),
                    artifact["sha256"],
                )


if __name__ == "__main__":
    unittest.main()
