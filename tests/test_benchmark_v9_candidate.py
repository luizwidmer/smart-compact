from __future__ import annotations

import unittest
import tomllib

import scripts.benchmark_v8 as benchmark_v8
import scripts.benchmark_v9_candidate as candidate


class V9CandidateRunnerTests(unittest.TestCase):
    def test_candidate_changes_only_parent_contract_knobs(self) -> None:
        candidate_profile = tomllib.loads(
            candidate.CANDIDATE_PROFILE.read_text(encoding="utf-8")
        )
        v8_profile = tomllib.loads(benchmark_v8.V8_PROFILE.read_text(encoding="utf-8"))
        candidate_instructions = candidate_profile.pop("developer_instructions")
        v8_profile.pop("developer_instructions")
        self.assertEqual(candidate_profile, v8_profile)

        policy = candidate.CANDIDATE_POLICY.read_text(encoding="utf-8")
        policy_contract = policy[policy.index("Minimize parent-model token use") :]
        self.assertEqual(candidate_instructions.strip(), policy_contract.strip())
        self.assertIn("There is no fixed worker cap", candidate_instructions)

    def test_argument_guard_accepts_only_explicit_v8_evaluator_arms(self) -> None:
        self.assertEqual(
            candidate.validate_wrapper_args(
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
                candidate.validate_wrapper_args(argv)

    def test_context_rebinds_candidate_and_restores_globals(self) -> None:
        original_specs = {
            arm: benchmark_v8.ARM_SPECS[arm] for arm in candidate.V8_ARMS
        }
        original_preflight = benchmark_v8.SPARK_AVAILABLE_INSTRUCTION
        controls = {
            arm: benchmark_v8.ARM_SPECS[arm] for arm in candidate.CONTROL_ARMS
        }

        with candidate.configured_candidate_arms():
            for arm, original in original_specs.items():
                rebound = benchmark_v8.ARM_SPECS[arm]
                self.assertEqual(rebound.profile_path, candidate.CANDIDATE_PROFILE)
                self.assertEqual(rebound.policy_path, candidate.CANDIDATE_POLICY)
                self.assertEqual(rebound.routing_mode, original.routing_mode)
                self.assertEqual(rebound.spark_enabled, original.spark_enabled)
                self.assertEqual(rebound.multi_agent, original.multi_agent)
                self.assertEqual(rebound.skill_input, original.skill_input)
                self.assertFalse(rebound.skill_input)
            self.assertEqual(
                benchmark_v8.SPARK_AVAILABLE_INSTRUCTION,
                candidate.CANDIDATE_SPARK_AVAILABLE_INSTRUCTION,
            )
            self.assertEqual(
                {
                    arm: benchmark_v8.ARM_SPECS[arm]
                    for arm in candidate.CONTROL_ARMS
                },
                controls,
            )

        self.assertEqual(
            {arm: benchmark_v8.ARM_SPECS[arm] for arm in candidate.V8_ARMS},
            original_specs,
        )
        self.assertEqual(
            benchmark_v8.SPARK_AVAILABLE_INSTRUCTION,
            original_preflight,
        )

    def test_metadata_and_auto_config_bind_the_candidate(self) -> None:
        with candidate.configured_candidate_arms():
            metadata = benchmark_v8.arm_metadata(list(candidate.V8_ARMS))
            profiles = benchmark_v8.load_arm_profiles(list(candidate.V8_ARMS))
            auto_config = benchmark_v8.build_arm_config(
                benchmark_v8.ARM_SPECS["v8-spark-auto"],
                profiles["v8-spark-auto"],
            )
            local_config = benchmark_v8.build_arm_config(
                benchmark_v8.ARM_SPECS["v8-no-spark"],
                profiles["v8-no-spark"],
            )

        for row in metadata.values():
            self.assertEqual(row["profile_path"], str(candidate.CANDIDATE_PROFILE))
            self.assertEqual(row["policy_path"], str(candidate.CANDIDATE_POLICY))
            self.assertEqual(len(row["profile_sha256"]), 64)
            self.assertEqual(len(row["policy_sha256"]), 64)
            self.assertFalse(row["skill_input"])
        self.assertIn(
            "positive-expected-return gate", auto_config["developer_instructions"]
        )
        self.assertNotIn(
            "positive-expected-return gate", local_config["developer_instructions"]
        )


if __name__ == "__main__":
    unittest.main()
