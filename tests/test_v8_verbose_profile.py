from __future__ import annotations

import copy
import unittest
import tomllib
from pathlib import Path

import scripts.benchmark_v8 as benchmark_v8


ROOT = Path(__file__).resolve().parents[1]
MECHY_PROFILE = ROOT / "profiles" / "smart-compact-v8.config.toml"
VERBOSE_PROFILE = ROOT / "benchmarks" / "experiments" / "v8-verbose" / "profile.config.toml"
VERBOSE_POLICY = ROOT / "benchmarks" / "experiments" / "v8-verbose" / "SKILL.md"


class V8VerboseProfileTests(unittest.TestCase):
    def setUp(self) -> None:
        self.mechy = tomllib.loads(MECHY_PROFILE.read_text(encoding="utf-8"))
        self.verbose = tomllib.loads(VERBOSE_PROFILE.read_text(encoding="utf-8"))

    def test_profile_changes_only_parent_developer_instructions(self) -> None:
        mechy = copy.deepcopy(self.mechy)
        verbose = copy.deepcopy(self.verbose)
        mechy_instructions = mechy.pop("developer_instructions")
        verbose_instructions = verbose.pop("developer_instructions")

        self.assertEqual(verbose, mechy)
        self.assertNotEqual(verbose_instructions, mechy_instructions)
        self.assertEqual(self.verbose["model_verbosity"], "low")
        self.assertEqual(self.verbose["model_reasoning_summary"], "none")
        self.assertEqual(self.verbose["personality"], "none")
        self.assertEqual(self.verbose["tool_output_token_limit"], 1500)
        self.assertEqual(self.verbose["compact_prompt"], self.mechy["compact_prompt"])

    def test_policy_is_exact_natural_language_mirror(self) -> None:
        policy = VERBOSE_POLICY.read_text(encoding="utf-8")
        instructions = policy.split("## Instructions\n\n", 1)[1].strip()
        profile_instructions = self.verbose["developer_instructions"].strip()

        self.assertEqual(instructions, profile_instructions)
        self.assertGreater(len(instructions.split()), 150)
        for machine_fragment in ("objective=", "delegate.when=", "workers=", "parent="):
            self.assertNotIn(machine_fragment, instructions)
        for meaning in (
            "without weakening correctness, safety, or the requested scope",
            "run the supplied acceptance command verbatim once",
            "Spawn before the parent reads worker-owned paths",
            "smallest useful worker set, but impose no fixed cap",
            "own multiple named partitions",
            "Consume each accepted handoff once",
            "drain every worker",
            "without substitution and do not probe again",
            "changed paths, decisive verification, blockers",
        ):
            self.assertIn(meaning, instructions)

    def test_rendered_configs_hold_every_non_treatment_field_constant(self) -> None:
        verbose_profile = benchmark_v8.load_profile(VERBOSE_PROFILE)
        mechy_profile = benchmark_v8.load_profile(MECHY_PROFILE)
        for arm in ("v8-no-spark", "v8-spark-forced", "v8-spark-auto"):
            with self.subTest(arm=arm):
                spec = benchmark_v8.ARM_SPECS[arm]
                mechy = benchmark_v8.build_arm_config(spec, mechy_profile)
                verbose = benchmark_v8.build_arm_config(spec, verbose_profile)
                mechy_instructions = mechy.pop("developer_instructions")
                verbose_instructions = verbose.pop("developer_instructions")
                self.assertEqual(verbose, mechy)
                self.assertNotEqual(verbose_instructions, mechy_instructions)
                self.assertTrue(
                    verbose_instructions.rstrip().endswith(
                        benchmark_v8.BENCHMARK_RTK_INSTRUCTION.strip()
                    )
                )
                if arm == "v8-spark-auto":
                    self.assertIn(benchmark_v8.SPARK_AVAILABLE_INSTRUCTION.strip(), verbose_instructions)

    def test_forced_worker_runtime_is_unchanged(self) -> None:
        mechy_config, mechy_identity = benchmark_v8.build_forced_worker_config(self.mechy)
        verbose_config, verbose_identity = benchmark_v8.build_forced_worker_config(self.verbose)
        self.assertEqual(verbose_config, mechy_config)
        self.assertEqual(verbose_identity, mechy_identity)


if __name__ == "__main__":
    unittest.main()
