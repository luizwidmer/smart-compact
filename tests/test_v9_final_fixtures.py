from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts import benchmark_v8
from scripts import benchmark_v9_final as benchmark


ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "benchmarks" / "agentic-v9-final.json"


class V9FinalFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cases = benchmark_v8.load_cases(CASES)

    def test_four_fresh_heldout_shapes_are_exact(self) -> None:
        self.assertEqual(len(self.cases), 4)
        self.assertEqual(
            {case["category"] for case in self.cases},
            {"implementation", "migration", "handoff", "general"},
        )
        self.assertTrue(all(case["split"] == "held-out" for case in self.cases))
        historical_ids: set[str] = set()
        for path in (ROOT / "benchmarks").glob("agentic*.json"):
            if path == CASES:
                continue
            payload = json.loads(path.read_text(encoding="utf-8"))
            historical_ids.update(
                case.get("id")
                for case in payload.get("cases", [])
                if isinstance(case, dict) and isinstance(case.get("id"), str)
            )
        self.assertFalse({case["id"] for case in self.cases} & historical_ids)

    def test_spark_and_local_treatments_match_selected_shapes(self) -> None:
        by_shape = {case["category"]: case for case in self.cases}
        for shape in benchmark.SPARK_SHAPES:
            delegation = by_shape[shape]["delegation"]
            self.assertEqual(delegation["mode"], "required_when_available")
            self.assertEqual(delegation["worker_io"], "read_only")
            self.assertGreaterEqual(len(delegation["expected_partitions"]), 3)
            self.assertIsNone(delegation["spawned_workers"]["max"])
        for shape in benchmark.LOCAL_SHAPES:
            delegation = by_shape[shape]["delegation"]
            self.assertEqual(delegation["mode"], "forbidden")
            self.assertEqual(delegation["spawned_workers"], {"min": 0, "max": 0})
            self.assertEqual(delegation["expected_partitions"], [])

    def test_fixture_seed_fails_and_gold_passes_exactly(self) -> None:
        validation = benchmark_v8.validate_v8_fixtures(self.cases)
        self.assertTrue(validation["ok"])
        for row in validation["cases"]:
            with self.subTest(case=row["case_id"]):
                self.assertEqual(row["seed_score_pct"], 0.0)
                self.assertEqual(row["gold_score_pct"], 100.0)
                self.assertEqual(row["gold_after_acceptance_score_pct"], 100.0)
                self.assertTrue(row["gold_acceptance_ok"])
                self.assertTrue(row["gold_scope_ok"])
                self.assertTrue(row["reset_reproducible"])

    def test_final_matrix_binds_required_models_and_efforts(self) -> None:
        observed = {
            (cell.task_shape, cell.model, cell.effort)
            for cell in benchmark.build_matrix(self.cases)
        }
        self.assertEqual(
            observed,
            {
                ("implementation", "gpt-5.6-sol", "medium"),
                ("migration", "gpt-5.6-sol", "high"),
                ("handoff", "gpt-5.6-luna", "xhigh"),
                ("general", "gpt-5.6-luna", "max"),
            },
        )


if __name__ == "__main__":
    unittest.main()
