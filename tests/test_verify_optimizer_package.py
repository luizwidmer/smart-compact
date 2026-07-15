from __future__ import annotations

import copy
import unittest
from pathlib import Path
from unittest import mock

from scripts import verify_optimizer_package as verifier


ROOT = Path(__file__).parents[1]


class VerifyOptimizerPackageTests(unittest.TestCase):
    def test_replays_exact_bound_totals(self) -> None:
        summary = verifier.verify(ROOT)
        self.assertTrue(summary["verified"])
        self.assertEqual(summary["cells"], 21)
        self.assertEqual(summary["allTerseParentTokens"], 4_509_801)
        self.assertEqual(summary["selectedParentTokens"], 3_430_364)
        self.assertEqual(summary["parentTokensSaved"], 1_079_437)
        self.assertEqual(summary["parentTokenReductionPct"], 23.935)
        self.assertEqual(
            summary["selectedCellsByLane"],
            {"v6": 4, "v8-natural": 17},
        )

    def test_rejects_source_hash_drift(self) -> None:
        table = verifier.load_table(ROOT / "optimizer" / "selection.json")
        drifted = copy.deepcopy(table)
        drifted["sources"][0]["sha256"] = "0" * 64
        with mock.patch.object(verifier, "load_table", return_value=drifted):
            with self.assertRaisesRegex(verifier.VerificationError, "source hash mismatch"):
                verifier.verify(ROOT)


if __name__ == "__main__":
    unittest.main()
