from __future__ import annotations

import collections
import copy
import unittest

import scripts.benchmark_v8 as benchmark_v8
import scripts.benchmark_v9_final as benchmark


def synthetic_cases() -> list[dict[str, str]]:
    return [
        {"id": "impl-case", "category": "implementation"},
        {"id": "migration-case", "category": "migration"},
        {"id": "handoff-case", "category": "handoff"},
        {"id": "general-case", "category": "general"},
    ]


class FinalMatrixTests(unittest.TestCase):
    def test_matrix_is_exactly_fourteen_unique_one_pass_cells(self) -> None:
        matrix = benchmark.build_matrix(synthetic_cases())
        self.assertEqual(len(matrix), 14)
        self.assertEqual(len({cell.cell_id for cell in matrix}), 14)
        self.assertEqual(
            collections.Counter(cell.arm for cell in matrix),
            {
                benchmark.V6_ARM: 4,
                benchmark.V8_ARM: 4,
                benchmark.V9_SELECTED_SPARK_ARM: 2,
                benchmark.V9_SELECTED_LOCAL_ARM: 2,
                benchmark.V9_LOCAL_COUNTERFACTUAL_ARM: 2,
            },
        )
        self.assertEqual(
            collections.Counter(cell.task_shape for cell in matrix),
            {"implementation": 4, "migration": 4, "handoff": 3, "general": 3},
        )

    def test_selected_routes_and_counterfactuals_match_task_shapes(self) -> None:
        matrix = benchmark.build_matrix(synthetic_cases())
        by_shape = {
            shape: {cell.arm for cell in matrix if cell.task_shape == shape}
            for shape in benchmark.TASK_SHAPES
        }
        for shape in benchmark.SPARK_SHAPES:
            self.assertIn(benchmark.V9_SELECTED_SPARK_ARM, by_shape[shape])
            self.assertIn(benchmark.V9_LOCAL_COUNTERFACTUAL_ARM, by_shape[shape])
            self.assertNotIn(benchmark.V9_SELECTED_LOCAL_ARM, by_shape[shape])
        for shape in benchmark.LOCAL_SHAPES:
            self.assertIn(benchmark.V9_SELECTED_LOCAL_ARM, by_shape[shape])
            self.assertNotIn(benchmark.V9_SELECTED_SPARK_ARM, by_shape[shape])
            self.assertNotIn(benchmark.V9_LOCAL_COUNTERFACTUAL_ARM, by_shape[shape])

    def test_matrix_covers_two_models_and_four_efforts(self) -> None:
        matrix = benchmark.build_matrix(synthetic_cases())
        settings = {
            (cell.task_shape, cell.model, cell.effort)
            for cell in matrix
        }
        self.assertEqual(
            settings,
            {
                ("implementation", "gpt-5.6-sol", "medium"),
                ("migration", "gpt-5.6-sol", "high"),
                ("handoff", "gpt-5.6-luna", "xhigh"),
                ("general", "gpt-5.6-luna", "max"),
            },
        )

    def test_manifest_requires_exactly_one_case_per_shape(self) -> None:
        duplicate = synthetic_cases() + [{"id": "impl-two", "category": "implementation"}]
        missing = synthetic_cases()[:-1]
        for cases in (duplicate, missing):
            with self.subTest(cases=cases), self.assertRaises(ValueError):
                benchmark.build_matrix(cases)

    def test_matrix_rows_are_self_validating(self) -> None:
        matrix = benchmark.build_matrix(synthetic_cases())
        rows = benchmark.matrix_rows(matrix)
        self.assertEqual(benchmark.validate_matrix_rows(rows), matrix)
        mutated = copy.deepcopy(rows)
        mutated[0]["effort"] = "high"
        with self.assertRaises(ValueError):
            benchmark.validate_matrix_rows(mutated)


class FinalRunnerContractTests(unittest.TestCase):
    def test_context_registers_final_arms_and_restores_shared_runner(self) -> None:
        original_specs = dict(benchmark_v8.ARM_SPECS)
        original_builder = benchmark_v8.build_arm_config
        with benchmark.configured_final_runner():
            for arm in benchmark.PHYSICAL_ARMS:
                self.assertIn(arm, benchmark_v8.ARM_SPECS)
            spark = benchmark_v8.ARM_SPECS[benchmark.V9_SELECTED_SPARK_ARM]
            self.assertTrue(spark.spark_enabled)
            self.assertTrue(spark.multi_agent)
            self.assertEqual(spark.routing_mode, "auto")
            self.assertFalse(spark.skill_input)
            self.assertIsNot(benchmark_v8.build_arm_config, original_builder)
        self.assertEqual(benchmark_v8.ARM_SPECS, original_specs)
        self.assertIs(benchmark_v8.build_arm_config, original_builder)

    def test_selected_spark_uses_config_only_without_availability_prompt(self) -> None:
        spec = benchmark._configured_specs()[benchmark.V9_SELECTED_SPARK_ARM]
        profile = {"developer_instructions": "minimal routing contract"}
        config = benchmark.build_final_arm_config(
            benchmark_v8.build_arm_config,
            spec,
            profile,
        )
        expected = (
            profile["developer_instructions"]
            + "\n\n"
            + benchmark_v8.BENCHMARK_RTK_INSTRUCTION.rstrip()
            + "\n"
        )
        self.assertEqual(config["developer_instructions"], expected)
        self.assertNotIn(
            benchmark_v8.SPARK_AVAILABLE_INSTRUCTION.strip(),
            config["developer_instructions"],
        )
        self.assertTrue(config["features"]["multi_agent"])

    def test_every_nonselected_spark_arm_is_configured_no_spark(self) -> None:
        specs = benchmark._configured_specs()
        for arm, spec in specs.items():
            if arm == benchmark.V9_SELECTED_SPARK_ARM:
                continue
            with self.subTest(arm=arm):
                self.assertFalse(spec.spark_enabled)
                self.assertFalse(spec.multi_agent)
                self.assertEqual(spec.routing_mode, "none")

    def test_task_gate_keeps_all_functional_requirements_hard(self) -> None:
        valid = {
            "task_pass": True,
            "grade": {"ok": True, "score_pct": 100.0},
            "scope_ok": True,
            "acceptance_observed": True,
            "usage_complete": True,
            "rtk_ok": True,
            "no_active_children": True,
            "parent_total_tokens": 100,
        }
        self.assertTrue(benchmark.task_gate_pass(valid))
        for key in (
            "task_pass",
            "scope_ok",
            "acceptance_observed",
            "usage_complete",
            "rtk_ok",
            "no_active_children",
        ):
            mutated = copy.deepcopy(valid)
            mutated[key] = False
            with self.subTest(key=key):
                self.assertFalse(benchmark.task_gate_pass(mutated))


if __name__ == "__main__":
    unittest.main()
