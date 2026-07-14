from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.open_app_task import app_server_command, load_profile, task_url, thread_start_params


class AppLauncherTests(unittest.TestCase):
    def test_app_server_command_applies_startup_feature_overrides(self) -> None:
        self.assertEqual(
            app_server_command("codex", ["features.multi_agent=false"]),
            [
                "codex",
                "-c",
                "features.multi_agent=false",
                "app-server",
                "--listen",
                "stdio://",
            ],
        )

    def test_loads_profile_and_builds_thread_override(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            profile = root / "smart-compact.config.toml"
            profile.write_text(
                'model_verbosity = "low"\ntool_output_token_limit = 4000\n',
                encoding="utf-8",
            )
            config = load_profile(profile)
            params = thread_start_params(root, config)

            self.assertEqual(params["cwd"], str(root))
            self.assertFalse(params["ephemeral"])
            self.assertEqual(params["config"]["model_verbosity"], "low")
            self.assertEqual(params["config"]["tool_output_token_limit"], 4000)
            self.assertTrue(thread_start_params(root, config, ephemeral=True)["ephemeral"])

    def test_task_url_uses_official_thread_deep_link(self) -> None:
        self.assertEqual(task_url("thread-123"), "codex://threads/thread-123")

    def test_empty_profile_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            profile = Path(directory) / "empty.toml"
            profile.write_text("", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "profile is empty"):
                load_profile(profile)


if __name__ == "__main__":
    unittest.main()
