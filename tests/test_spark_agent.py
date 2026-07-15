from __future__ import annotations

import tempfile
import tomllib
import unittest
from pathlib import Path

from scripts.install_spark_agent import install_agent
from scripts.install_codex_profile import install_profile


ROOT = Path(__file__).parents[1]


class SparkAgentTests(unittest.TestCase):
    def test_agent_pins_benchmarked_model_and_effort(self) -> None:
        config = tomllib.loads(
            (ROOT / ".codex" / "agents" / "spark-worker.toml").read_text(encoding="utf-8")
        )
        self.assertEqual(config["name"], "spark_worker")
        self.assertEqual(config["model"], "gpt-5.3-codex-spark")
        self.assertEqual(config["model_reasoning_effort"], "medium")

    def test_agent_declares_safe_scope_and_fallback(self) -> None:
        config = tomllib.loads(
            (ROOT / ".codex" / "agents" / "spark-worker.toml").read_text(encoding="utf-8")
        )
        description = config["description"].lower()
        instructions = config["developer_instructions"]
        self.assertIn("continues locally", description)
        self.assertIn("without substituting another agent", description)
        self.assertLessEqual(len(instructions.split()), 16)
        for contract in (
            "scope=assigned_partitions_and_paths_only",
            "reads=batch",
            "edits=apply_patch_only",
            "shell.first_word=rtk",
            "shell.cwd_change=forbidden",
            "shell.raw=rtk_proxy",
            "delegation=forbidden",
            "decisions.architecture_security_product_destructive=forbidden",
            "acceptance=once",
            "retry=diagnosed_failure_only",
            "return=partition_ids,changed_paths_or_facts_with_provenance,acceptance,blocker",
        ):
            with self.subTest(contract=contract):
                self.assertIn(contract, instructions)

    def test_installer_writes_new_agent_atomically(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "agents" / "spark-worker.toml"
            self.assertEqual(install_agent("model = 'spark'\n", target), "installed")
            self.assertEqual(target.read_text(encoding="utf-8"), "model = 'spark'\n")

    def test_installer_does_not_overwrite_without_force(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "spark-worker.toml"
            target.write_text("existing\n", encoding="utf-8")
            self.assertEqual(install_agent("replacement\n", target), "conflict")
            self.assertEqual(target.read_text(encoding="utf-8"), "existing\n")


class SmartCompactProfileTests(unittest.TestCase):
    def test_profile_uses_benchmarked_native_controls(self) -> None:
        self.assertEqual(
            (ROOT / "profiles" / "smart-compact.config.toml").read_bytes(),
            (ROOT / "profiles" / "smart-compact-v8.config.toml").read_bytes(),
        )
        config = tomllib.loads(
            (ROOT / "profiles" / "smart-compact.config.toml").read_text(encoding="utf-8")
        )
        self.assertEqual(config["model_verbosity"], "low")
        self.assertEqual(config["model_reasoning_summary"], "none")
        self.assertEqual(config["personality"], "none")
        self.assertNotIn("model_auto_compact_token_limit", config)
        self.assertNotIn("model_auto_compact_token_limit_scope", config)
        self.assertEqual(config["tool_output_token_limit"], 1500)
        self.assertFalse(config["agents"]["interrupt_message"])
        self.assertIn("format=lossless_key_value", config["compact_prompt"])
        self.assertIn("shell.wrapper=literal_every_command_and_retry", config["developer_instructions"])
        self.assertIn("workers=smallest_useful;cap:none", config["developer_instructions"])
        self.assertIn("multi_partition:true", config["developer_instructions"])
        self.assertIn("owns_decisions+integration+final_acceptance", config["developer_instructions"])
        self.assertIn("spark_unavailable=local,no_substitution", config["developer_instructions"])

    def test_profile_installer_preserves_conflicting_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "smart-compact.config.toml"
            target.write_text("existing\n", encoding="utf-8")
            self.assertEqual(install_profile("replacement\n", target), "conflict")
            self.assertEqual(target.read_text(encoding="utf-8"), "existing\n")


if __name__ == "__main__":
    unittest.main()
