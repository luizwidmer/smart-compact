from __future__ import annotations

import copy
import unittest
from pathlib import Path
from unittest import mock

from scripts import verify_optimizer_package as verifier


ROOT = Path(__file__).parents[1]


class VerifyOptimizerPackageTests(unittest.TestCase):
    def test_verifies_definitive_state_aware_package(self) -> None:
        summary = verifier.verify(ROOT)
        self.assertTrue(summary["verified"])
        self.assertEqual(summary["product"], "smart-compact-v9")
        self.assertEqual(
            summary["selectableProfiles"],
            ["smart-compact-v9", "smart-compact-v9-spark", "smart-compact-v9-v8"],
        )
        self.assertEqual(summary["localInstructionBytes"], 259)
        self.assertEqual(summary["sparkInstructionBytes"], 769)
        selection = summary["selectionEvidence"]
        self.assertEqual(
            selection["status"],
            "post_matrix_deployable_hybrid_selection_not_blinded_confirmation",
        )
        self.assertEqual(selection["taskCorrectCells"], 16)
        self.assertEqual(selection["official"]["standard_parent_tokens"], 3_138_482)
        self.assertEqual(selection["official"]["v6_parent_tokens"], 3_361_104)
        self.assertEqual(selection["official"]["v8_parent_tokens"], 3_004_930)
        self.assertEqual(selection["official"]["v9_parent_tokens"], 2_607_766)
        self.assertEqual(selection["official"]["v9_spawned_workers"], 1)
        self.assertEqual(selection["fresh"]["v9_parent_tokens"], 462_901)
        self.assertEqual(selection["combined"]["v9_parent_tokens"], 3_070_667)
        self.assertEqual(summary["uniformStateCandidate"], "rejected")
        self.assertEqual(
            summary["uniformStateCost"],
            {
                "status": "rejected",
                "parent_tokens": 3_817_102,
                "state_aware_parent_tokens": 2_607_766,
                "state_aware_saved_tokens": 1_209_336,
                "state_aware_reduction_pct": 31.682,
            },
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
