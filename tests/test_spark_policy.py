from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
CASES_PATH = ROOT / "benchmarks" / "spark-cases.json"


class SparkPolicyDecisionTests(unittest.TestCase):
    @staticmethod
    def _spark_decision(case: dict[str, object]) -> str:
        return (
            "spark"
            if (
                case["independent"]
                and case["parallel"]
                and case["text_only"]
                and case["mechanical"]
                and case["acceptance_check"]
                and case["risk"] == "normal"
                and (case["allowance_priority"] or case["paired_parent_savings"])
            )
            else "local"
        )

    def test_schema_and_unique_ids(self) -> None:
        cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))

        self.assertIsInstance(cases, list)

        required_fields = {
            "id",
            "expected_decision",
            "independent",
            "parallel",
            "text_only",
            "mechanical",
            "acceptance_check",
            "allowance_priority",
            "paired_parent_savings",
            "estimated_tool_calls",
            "target_count",
            "risk",
        }

        seen_ids: set[str] = set()
        for case in cases:
            self.assertIsInstance(case, dict)
            self.assertEqual(set(case.keys()), required_fields)
            self.assertNotIn(case["id"], seen_ids)
            seen_ids.add(case["id"])

            self.assertIsInstance(case["id"], str)
            self.assertIn(case["expected_decision"], {"spark", "local"})
            self.assertIsInstance(case["independent"], bool)
            self.assertIsInstance(case["parallel"], bool)
            self.assertIsInstance(case["text_only"], bool)
            self.assertIsInstance(case["mechanical"], bool)
            self.assertIsInstance(case["acceptance_check"], bool)
            self.assertIsInstance(case["allowance_priority"], bool)
            self.assertIsInstance(case["paired_parent_savings"], bool)
            self.assertIsInstance(case["estimated_tool_calls"], int)
            self.assertIsInstance(case["target_count"], int)
            self.assertIsInstance(case["risk"], str)

        self.assertGreaterEqual(len(cases), 8)
        self.assertTrue(
            any(
                case["expected_decision"] == "spark" and case["target_count"] < 6
                for case in cases
            ),
            "Spark eligibility must not have a fixed six-target floor",
        )

    def test_oracle_decisions(self) -> None:
        cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))

        for case in cases:
            with self.subTest(case_id=case["id"]):
                self.assertEqual(case["expected_decision"], self._spark_decision(case))


if __name__ == "__main__":
    unittest.main()
