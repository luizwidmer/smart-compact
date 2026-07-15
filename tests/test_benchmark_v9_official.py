from __future__ import annotations

import collections
import copy
import unittest

from scripts import benchmark_v9_official as benchmark


class OfficialMatrixTests(unittest.TestCase):
    def test_matrix_is_exactly_twelve_unique_one_pass_cells(self) -> None:
        matrix = benchmark.build_matrix(benchmark.load_official_cases())
        self.assertEqual(len(matrix), 12)
        self.assertEqual(len({cell.cell_id for cell in matrix}), 12)
        self.assertEqual(
            collections.Counter(cell.arm for cell in matrix),
            {
                benchmark.final.V9_SELECTED_SPARK_ARM: 4,
                benchmark.final.V9_SELECTED_LOCAL_ARM: 8,
            },
        )

    def test_routes_are_implementation_spark_and_others_local(self) -> None:
        matrix = benchmark.build_matrix(benchmark.load_official_cases())
        by_case = {
            case_id: {cell.arm for cell in matrix if cell.case_id == case_id}
            for case_id in benchmark.CASE_SOURCES
        }
        self.assertEqual(
            by_case["legacy-calculator"],
            {benchmark.final.V9_SELECTED_SPARK_ARM},
        )
        self.assertEqual(
            by_case["legacy-relay-bench"],
            {benchmark.final.V9_SELECTED_LOCAL_ARM},
        )
        self.assertEqual(
            by_case["monorepo-sdk-migration"],
            {benchmark.final.V9_SELECTED_LOCAL_ARM},
        )

    def test_each_case_covers_two_models_and_four_efforts(self) -> None:
        matrix = benchmark.build_matrix(benchmark.load_official_cases())
        for case_id in benchmark.CASE_SOURCES:
            observed = {
                (cell.model, cell.effort)
                for cell in matrix
                if cell.case_id == case_id
            }
            self.assertEqual(observed, set(benchmark.SETTINGS))

    def test_execution_order_is_deterministic(self) -> None:
        matrix = benchmark.build_matrix(benchmark.load_official_cases())
        first = benchmark.execution_order_rows(matrix)
        self.assertEqual(first, benchmark.execution_order_rows(matrix))
        self.assertNotEqual(first, benchmark.execution_order_rows(matrix, benchmark.SEED + 1))

    def test_matrix_rows_reject_treatment_drift(self) -> None:
        matrix = benchmark.build_matrix(benchmark.load_official_cases())
        rows = benchmark.matrix_rows(matrix)
        self.assertEqual(benchmark.validate_matrix_rows(rows), matrix)
        mutated = copy.deepcopy(rows)
        mutated[0]["arm"] = benchmark.final.V9_SELECTED_LOCAL_ARM
        mutated[0]["cell_id"] = (
            f"{mutated[0]['case_id']}::{mutated[0]['model']}::"
            f"{mutated[0]['effort']}::{mutated[0]['arm']}"
        )
        with self.assertRaises(ValueError):
            benchmark.validate_matrix_rows(mutated)

    def test_functional_gate_does_not_turn_ephemeral_telemetry_into_task_failure(self) -> None:
        result = {
            "task_pass": True,
            "grade": {"ok": True, "score_pct": 100.0},
            "scope_ok": True,
            "acceptance_observed": True,
            "usage_complete": True,
            "rtk_ok": True,
            "parent_total_tokens": 100,
            "no_active_children": False,
            "child_completion_ok": False,
        }
        self.assertTrue(benchmark.functional_task_pass(result))
        for key in ("task_pass", "scope_ok", "acceptance_observed", "usage_complete", "rtk_ok"):
            mutated = copy.deepcopy(result)
            mutated[key] = False
            with self.subTest(key=key):
                self.assertFalse(benchmark.functional_task_pass(mutated))


if __name__ == "__main__":
    unittest.main()
