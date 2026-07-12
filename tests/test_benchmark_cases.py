from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.compact_guard import classify


class BenchmarkCaseTests(unittest.TestCase):
    def test_expected_modes_match_guard(self) -> None:
        path = Path(__file__).parents[1] / "benchmarks" / "cases.json"
        cases = json.loads(path.read_text(encoding="utf-8"))

        mismatches = {
            case["id"]: {
                "expected": case["expected_mode"],
                "actual": classify(case["source"])["mode"],
            }
            for case in cases
            if classify(case["source"])["mode"] != case["expected_mode"]
        }
        self.assertEqual(mismatches, {})


if __name__ == "__main__":
    unittest.main()
