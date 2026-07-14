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
        text = f"{config['description']}\n{config['developer_instructions']}".lower()
        self.assertIn("retry once", text)
        self.assertIn("do not make architecture", text)
        self.assertIn("acceptance check", text)

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
        config = tomllib.loads(
            (ROOT / "profiles" / "smart-compact.config.toml").read_text(encoding="utf-8")
        )
        self.assertEqual(config["model_verbosity"], "low")
        self.assertEqual(config["model_reasoning_summary"], "none")
        self.assertEqual(config["tool_output_token_limit"], 4000)
        self.assertFalse(config["agents"]["interrupt_message"])
        self.assertIn("lossless operational state", config["compact_prompt"])
        self.assertIn("every exec_command command must begin with rtk", config["developer_instructions"])
        self.assertIn("MUST call spawn_agent", config["developer_instructions"])
        self.assertIn("at least three tool calls", config["developer_instructions"])
        self.assertIn('agent_type="spark_worker"', config["developer_instructions"])
        self.assertIn("do not substitute default", config["developer_instructions"])

    def test_profile_installer_preserves_conflicting_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "smart-compact.config.toml"
            target.write_text("existing\n", encoding="utf-8")
            self.assertEqual(install_profile("replacement\n", target), "conflict")
            self.assertEqual(target.read_text(encoding="utf-8"), "existing\n")


if __name__ == "__main__":
    unittest.main()
