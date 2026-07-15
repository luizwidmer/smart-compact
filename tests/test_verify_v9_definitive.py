from __future__ import annotations

import unittest

from scripts import verify_v9_definitive as verifier


class DefinitiveV9VerifierTests(unittest.TestCase):
    def test_frozen_sources_rebuild_definitive_state_aware_metrics(self) -> None:
        report = verifier.build_report()

        self.assertEqual(report["status"], "v9_definitive_selection_verified")
        self.assertEqual(report["task_correct_cells"], 16)
        self.assertEqual(report["official"]["totals"]["v9_parent_tokens"], 2_607_766)
        self.assertEqual(report["official"]["totals"]["v9_saved_vs_standard"], 530_716)
        self.assertEqual(report["official"]["totals"]["v9_saved_vs_v6"], 753_338)
        self.assertEqual(report["official"]["totals"]["v9_saved_vs_v8"], 397_164)
        self.assertEqual(report["official"]["totals"]["v9_spawned_workers"], 1)
        self.assertEqual(report["fresh_additions"]["totals"]["v9_parent_tokens"], 462_901)
        self.assertEqual(report["combined"]["v9_parent_tokens"], 3_070_667)
        self.assertEqual(
            report["uniform_state_candidate"],
            {
                "status": "rejected",
                "parent_tokens": 3_817_102,
                "state_aware_parent_tokens": 2_607_766,
                "state_aware_saved_tokens": 1_209_336,
                "state_aware_reduction_pct": 31.682,
            },
        )

    def test_lane_map_keeps_spark_narrow_and_supports_native(self) -> None:
        self.assertEqual(
            verifier.official_lane("legacy-calculator", "gpt-5.6-luna", "max"),
            "v9-spark",
        )
        self.assertEqual(
            verifier.official_lane("legacy-calculator", "gpt-5.6-luna", "xhigh"),
            "v9-v8",
        )
        self.assertEqual(
            verifier.official_lane("monorepo-sdk-migration", "gpt-5.6-sol", "medium"),
            "native",
        )


if __name__ == "__main__":
    unittest.main()
