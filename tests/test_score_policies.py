from __future__ import annotations

import unittest
from pathlib import Path

from scripts.score_policies import policy_name, projected_calls, safety_score


ROOT = Path(__file__).parents[1]


class ScorePoliciesTests(unittest.TestCase):
    def test_promoted_policy_retains_all_safety_signals(self) -> None:
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        score, missing = safety_score(text)
        self.assertEqual(score, 6)
        self.assertEqual(missing, [])

    def test_projected_calls_are_positive_and_reduced(self) -> None:
        text = "Do not create a plan. Implement in one coherent patch. Run one scoped status check."
        calls = projected_calls(text, baseline_calls=23)
        self.assertGreaterEqual(calls, 1)
        self.assertLess(calls, 23)

    def test_skill_policy_name_uses_parent_directory(self) -> None:
        self.assertEqual(policy_name(Path("candidate-a/SKILL.md")), "candidate-a")
        self.assertEqual(policy_name(Path("SKILL.md")), "smart-compact")


if __name__ == "__main__":
    unittest.main()
