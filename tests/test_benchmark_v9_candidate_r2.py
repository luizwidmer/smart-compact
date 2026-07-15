from __future__ import annotations

import tomllib
import unittest

import scripts.benchmark_v8 as benchmark_v8
import scripts.benchmark_v9_candidate_r2 as candidate


class V9CandidateR2RunnerTests(unittest.TestCase):
    def test_profile_keeps_v8_runtime_knobs_and_mirrors_policy(self) -> None:
        profile = tomllib.loads(candidate.CANDIDATE_PROFILE.read_text(encoding="utf-8"))
        v8 = tomllib.loads(benchmark_v8.V8_PROFILE.read_text(encoding="utf-8"))
        instructions = profile.pop("developer_instructions")
        v8.pop("developer_instructions")
        self.assertEqual(profile, v8)
        policy = candidate.CANDIDATE_POLICY.read_text(encoding="utf-8")
        self.assertEqual(
            instructions.strip(),
            policy[policy.index("Minimize the parent model's token use") :].strip(),
        )

    def test_context_rebinds_paths_and_auto_preflight_then_restores(self) -> None:
        originals = {arm: benchmark_v8.ARM_SPECS[arm] for arm in candidate.V8_ARMS}
        original_preflight = benchmark_v8.SPARK_AVAILABLE_INSTRUCTION
        with candidate.configured_candidate_arms():
            for arm in candidate.V8_ARMS:
                self.assertEqual(
                    benchmark_v8.ARM_SPECS[arm].profile_path,
                    candidate.CANDIDATE_PROFILE,
                )
                self.assertEqual(
                    benchmark_v8.ARM_SPECS[arm].policy_path,
                    candidate.CANDIDATE_POLICY,
                )
            self.assertEqual(
                benchmark_v8.SPARK_AVAILABLE_INSTRUCTION,
                candidate.CANDIDATE_SPARK_AVAILABLE_INSTRUCTION,
            )
        self.assertEqual(
            {arm: benchmark_v8.ARM_SPECS[arm] for arm in candidate.V8_ARMS},
            originals,
        )
        self.assertEqual(benchmark_v8.SPARK_AVAILABLE_INSTRUCTION, original_preflight)

    def test_auto_only_receives_decisive_small_file_gate(self) -> None:
        with candidate.configured_candidate_arms():
            profiles = benchmark_v8.load_arm_profiles(list(candidate.V8_ARMS))
            auto = benchmark_v8.build_arm_config(
                benchmark_v8.ARM_SPECS["v8-spark-auto"],
                profiles["v8-spark-auto"],
            )["developer_instructions"]
            local = benchmark_v8.build_arm_config(
                benchmark_v8.ARM_SPECS["v8-no-spark"],
                profiles["v8-no-spark"],
            )["developer_instructions"]
        self.assertIn("one batched parent read is cheaper", auto)
        self.assertNotIn("one batched parent read is cheaper", local)


if __name__ == "__main__":
    unittest.main()
