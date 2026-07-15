from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.compact_guard import check, classify


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

    def test_official_candidates_cover_and_preserve_every_case(self) -> None:
        root = Path(__file__).parents[1]
        cases = json.loads((root / "benchmarks" / "cases.json").read_text(encoding="utf-8"))
        candidates = json.loads(
            (root / "benchmarks" / "candidates.forward.json").read_text(encoding="utf-8")
        )

        self.assertEqual(set(candidates), {case["id"] for case in cases})
        failures = {
            case["id"]: check(case["source"], candidates[case["id"]])["missing"]
            for case in cases
            if not check(case["source"], candidates[case["id"]])["ok"]
        }
        self.assertEqual(failures, {})


if __name__ == "__main__":
    unittest.main()
