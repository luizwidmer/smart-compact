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
        self.assertIn("continues locally", text)
        self.assertIn("without substituting another agent", text)
        self.assertIn("first word of every command string must be literal `rtk`", text)
        self.assertIn("never emit shell `cd` or `chdir`", text)
        self.assertIn("reject it yourself if its first word is not `rtk`", text)
        self.assertIn("never use raw `ls`", text)
        self.assertIn("normalized per-source facts", text)
        self.assertIn("at most six tool calls", text)
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
        self.assertEqual(
            (ROOT / "profiles" / "smart-compact.config.toml").read_bytes(),
            (ROOT / "profiles" / "smart-compact-v7.config.toml").read_bytes(),
        )
        config = tomllib.loads(
            (ROOT / "profiles" / "smart-compact.config.toml").read_text(encoding="utf-8")
        )
        self.assertEqual(config["model_verbosity"], "low")
        self.assertEqual(config["model_reasoning_summary"], "none")
        self.assertEqual(config["personality"], "none")
        self.assertEqual(config["model_auto_compact_token_limit"], 49152)
        self.assertEqual(config["model_auto_compact_token_limit_scope"], "body_after_prefix")
        self.assertEqual(config["tool_output_token_limit"], 2000)
        self.assertFalse(config["agents"]["interrupt_message"])
        self.assertIn("lossless operational handoff", config["compact_prompt"])
        self.assertIn("every exec_command string starts with rtk", config["developer_instructions"])
        self.assertIn("exact spark_worker role", config["developer_instructions"])
        self.assertIn("smallest concurrent worker set", config["developer_instructions"])
        self.assertIn("never apply a fixed global count", config["developer_instructions"])
        self.assertIn("One worker may own several nonoverlapping partitions", config["developer_instructions"])
        self.assertIn("Add another only when", config["developer_instructions"])
        self.assertIn("one final deterministic acceptance check", config["developer_instructions"])
        self.assertIn("without substituting another role", config["developer_instructions"])

    def test_profile_installer_preserves_conflicting_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "smart-compact.config.toml"
            target.write_text("existing\n", encoding="utf-8")
            self.assertEqual(install_profile("replacement\n", target), "conflict")
            self.assertEqual(target.read_text(encoding="utf-8"), "existing\n")


if __name__ == "__main__":
    unittest.main()
