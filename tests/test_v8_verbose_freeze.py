from __future__ import annotations

import hashlib
import json
import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
FREEZE = ROOT / "benchmarks" / "experiments" / "v8-verbose" / "freeze.json"


class V8VerboseFreezeTests(unittest.TestCase):
    def test_frozen_hashes_and_exact_matrix(self) -> None:
        payload = json.loads(FREEZE.read_text(encoding="utf-8"))
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["status"], "input_frozen_before_inference")
        matrix = payload["matrix"]
        self.assertEqual(matrix["total_cells"], 42)
        self.assertEqual(matrix["v8_no_spark_cells"], 21)
        self.assertEqual(matrix["v8_forced_spark_cells"], 12)
        self.assertEqual(matrix["v8_auto_spark_cells"], 9)
        self.assertEqual(matrix["standard_cells"], 0)
        self.assertEqual(matrix["v6_cells"], 0)
        for artifact in payload["artifacts"].values():
            path = ROOT / artifact["path"]
            self.assertTrue(path.is_file(), artifact["path"])
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), artifact["sha256"])

    def test_only_parent_instructions_change(self) -> None:
        mechy = tomllib.loads(
            (ROOT / "profiles" / "smart-compact-v8.config.toml").read_text(encoding="utf-8")
        )
        verbose = tomllib.loads(
            (
                ROOT
                / "benchmarks"
                / "experiments"
                / "v8-verbose"
                / "profile.config.toml"
            ).read_text(encoding="utf-8")
        )
        self.assertNotEqual(mechy["developer_instructions"], verbose["developer_instructions"])
        mechy.pop("developer_instructions")
        verbose.pop("developer_instructions")
        self.assertEqual(mechy, verbose)


if __name__ == "__main__":
    unittest.main()
