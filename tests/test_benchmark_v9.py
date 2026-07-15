from __future__ import annotations

import collections
import unittest

import scripts.benchmark_v8 as benchmark_v8
import scripts.benchmark_v9 as benchmark_v9


class V9MatrixTests(unittest.TestCase):
    def test_matrix_is_exactly_fifteen_unique_one_pass_cells(self) -> None:
        self.assertEqual(len(benchmark_v9.MATRIX), 15)
        self.assertEqual(
            len({cell.cell_id for cell in benchmark_v9.MATRIX}),
            15,
        )
        allocations = collections.Counter(cell.arm for cell in benchmark_v9.MATRIX)
        self.assertEqual(
            allocations,
            {
                benchmark_v9.V6_ARM: 4,
                benchmark_v9.V8_ARM: 4,
                benchmark_v9.V9_AUTO_ARM: 4,
                benchmark_v9.V9_NATURAL_ARM: 3,
            },
        )
        self.assertEqual(
            collections.Counter(cell.task_shape for cell in benchmark_v9.MATRIX),
            {"implementation": 3, "migration": 4, "handoff": 4, "general": 4},
        )

    def test_matrix_covers_the_four_frozen_parent_settings(self) -> None:
        settings = {
            (cell.case_id, cell.model, cell.effort)
            for cell in benchmark_v9.MATRIX
        }
        self.assertEqual(
            settings,
            {
                ("polyglot-record-normalizer", "gpt-5.6-sol", "medium"),
                ("workspace-permission-migration", "gpt-5.6-sol", "high"),
                ("incident-window-correlation", "gpt-5.6-luna", "xhigh"),
                ("ordered-entitlement-ledger", "gpt-5.6-luna", "max"),
            },
        )

    def test_implementation_reuse_is_exact_and_costs_no_cell(self) -> None:
        binding = benchmark_v9.validate_profile_binding()
        self.assertEqual(binding["v6_sha256"], binding["v9_implementation_sha256"])
        self.assertEqual(binding["equivalence"], "byte_identical_profile")
        self.assertEqual(
            benchmark_v9.IMPLEMENTATION_REUSE_BINDING["additional_inference_cells"],
            0,
        )
        implementation = [
            cell
            for cell in benchmark_v9.MATRIX
            if cell.case_id == "polyglot-record-normalizer"
        ]
        self.assertEqual(
            [cell.arm for cell in implementation],
            [benchmark_v9.V6_ARM, benchmark_v9.V8_ARM, benchmark_v9.V9_AUTO_ARM],
        )


class V9RunnerContractTests(unittest.TestCase):
    def test_context_registers_v9_arms_and_restores_v8_globals(self) -> None:
        original_specs = dict(benchmark_v8.ARM_SPECS)
        original_builder = benchmark_v8.build_arm_config
        with benchmark_v9.configured_v9_runner():
            for arm in benchmark_v9.PHYSICAL_ARMS:
                self.assertIn(arm, benchmark_v8.ARM_SPECS)
            auto = benchmark_v8.ARM_SPECS[benchmark_v9.V9_AUTO_ARM]
            self.assertTrue(auto.spark_enabled)
            self.assertTrue(auto.multi_agent)
            self.assertEqual(auto.routing_mode, "auto")
            self.assertFalse(auto.skill_input)
            self.assertIsNot(benchmark_v8.build_arm_config, original_builder)
        self.assertEqual(benchmark_v8.ARM_SPECS, original_specs)
        self.assertIs(benchmark_v8.build_arm_config, original_builder)

    def test_production_v9_auto_has_config_routing_and_no_prompt_preflight(self) -> None:
        with benchmark_v9.configured_v9_runner():
            profiles = benchmark_v8.load_arm_profiles([benchmark_v9.V9_AUTO_ARM])
            spec = benchmark_v8.ARM_SPECS[benchmark_v9.V9_AUTO_ARM]
            config = benchmark_v8.build_arm_config(
                spec,
                profiles[benchmark_v9.V9_AUTO_ARM],
            )
        profile = profiles[benchmark_v9.V9_AUTO_ARM]
        expected = (
            profile["developer_instructions"].rstrip()
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

    def test_controls_and_natural_lane_are_no_spark(self) -> None:
        with benchmark_v9.configured_v9_runner():
            specs = {
                arm: benchmark_v8.ARM_SPECS[arm]
                for arm in (
                    benchmark_v9.V6_ARM,
                    benchmark_v9.V8_ARM,
                    benchmark_v9.V9_NATURAL_ARM,
                )
            }
        for spec in specs.values():
            self.assertFalse(spec.spark_enabled)
            self.assertFalse(spec.multi_agent)
            self.assertEqual(spec.routing_mode, "none")

    def test_task_gate_recomputes_exact_acceptance_requirements(self) -> None:
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
        self.assertTrue(benchmark_v9.task_gate_pass(valid))
        for key in (
            "task_pass",
            "scope_ok",
            "acceptance_observed",
            "usage_complete",
            "rtk_ok",
            "no_active_children",
        ):
            mutated = dict(valid)
            mutated[key] = False
            with self.subTest(key=key):
                self.assertFalse(benchmark_v9.task_gate_pass(mutated))


class V9FixtureTests(unittest.TestCase):
    def test_fresh_manifest_and_gold_are_deterministic_and_exact(self) -> None:
        cases = benchmark_v8.load_cases(benchmark_v9.DEFAULT_CASES)
        self.assertEqual(
            [(case["id"], case["category"], case["split"]) for case in cases],
            [
                ("polyglot-record-normalizer", "implementation", "held-out"),
                ("workspace-permission-migration", "migration", "held-out"),
                ("incident-window-correlation", "handoff", "held-out"),
                ("ordered-entitlement-ledger", "general", "held-out"),
            ],
        )
        validation = benchmark_v8.validate_v8_fixtures(cases)
        self.assertTrue(validation["ok"])
        for row in validation["cases"]:
            self.assertTrue(row["reset_reproducible"])
            self.assertLess(row["seed_score_pct"], 100.0)
            self.assertEqual(row["gold_score_pct"], 100.0)
            self.assertEqual(row["gold_after_acceptance_score_pct"], 100.0)
            self.assertTrue(row["gold_acceptance_ok"])
            self.assertTrue(row["gold_scope_ok"])


if __name__ == "__main__":
    unittest.main()
