from __future__ import annotations

import unittest

import scripts.benchmark_v8 as benchmark_v8
import scripts.benchmark_v8_verbose as verbose_runner


class V8VerboseRunnerTests(unittest.TestCase):
    def test_argument_guard_accepts_only_explicit_v8_arms(self) -> None:
        self.assertEqual(
            verbose_runner.validate_wrapper_args(
                ["--arm", "v8-no-spark", "--arm=v8-spark-auto"]
            ),
            ("v8-no-spark", "v8-spark-auto"),
        )
        for argv in (
            [],
            ["--arm", "standard-no-spark"],
            ["--arm=v6-no-spark"],
            ["--arm", "v8-no-spark", "--v8-profile", "other.toml"],
            ["--arm=v8-no-spark", "--v8-profile=other.toml"],
            ["--arm", "v8-unknown"],
            ["--arm"],
        ):
            with self.subTest(argv=argv), self.assertRaises(ValueError):
                verbose_runner.validate_wrapper_args(argv)

    def test_context_rebinds_only_paths_and_restores_specs(self) -> None:
        originals = {arm: benchmark_v8.ARM_SPECS[arm] for arm in verbose_runner.V8_ARMS}
        controls = {arm: benchmark_v8.ARM_SPECS[arm] for arm in verbose_runner.CONTROL_ARMS}

        with verbose_runner.configured_verbose_arms():
            for arm, original in originals.items():
                rebound = benchmark_v8.ARM_SPECS[arm]
                self.assertEqual(rebound.profile_path, verbose_runner.VERBOSE_PROFILE)
                self.assertEqual(rebound.policy_path, verbose_runner.VERBOSE_POLICY)
                self.assertEqual(rebound.name, original.name)
                self.assertEqual(rebound.spark_enabled, original.spark_enabled)
                self.assertEqual(rebound.multi_agent, original.multi_agent)
                self.assertEqual(rebound.skill_input, original.skill_input)
                self.assertFalse(rebound.skill_input)
                self.assertEqual(rebound.routing_mode, original.routing_mode)
            self.assertEqual(
                {arm: benchmark_v8.ARM_SPECS[arm] for arm in verbose_runner.CONTROL_ARMS},
                controls,
            )

        self.assertEqual(
            {arm: benchmark_v8.ARM_SPECS[arm] for arm in verbose_runner.V8_ARMS},
            originals,
        )

    def test_arm_metadata_records_verbose_paths_and_hashes(self) -> None:
        with verbose_runner.configured_verbose_arms():
            metadata = benchmark_v8.arm_metadata(list(verbose_runner.V8_ARMS))
        for row in metadata.values():
            self.assertEqual(row["profile_path"], str(verbose_runner.VERBOSE_PROFILE))
            self.assertEqual(row["policy_path"], str(verbose_runner.VERBOSE_POLICY))
            self.assertEqual(len(row["profile_sha256"]), 64)
            self.assertEqual(len(row["policy_sha256"]), 64)
            self.assertFalse(row["skill_input"])


if __name__ == "__main__":
    unittest.main()
