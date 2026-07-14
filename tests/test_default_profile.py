from __future__ import annotations

import stat
import tempfile
import tomllib
import unittest
from pathlib import Path

from scripts.default_profile import (
    MANAGED_TOP_LEVEL_KEYS,
    promote_profile,
    render_promoted_config,
)


ROOT = Path(__file__).parents[1]
PROFILE = ROOT / "profiles" / "smart-compact.config.toml"


class DefaultProfileTests(unittest.TestCase):
    def test_render_preserves_unrelated_config_and_comments(self) -> None:
        base = """# user comment
model = "gpt-example"
model_reasoning_effort = "high"

[agents]
max_threads = 8

[plugins."example"]
enabled = true
"""
        rendered = render_promoted_config(PROFILE.read_text(encoding="utf-8"), base)
        parsed = tomllib.loads(rendered)
        profile = tomllib.loads(PROFILE.read_text(encoding="utf-8"))

        self.assertIn("# user comment\n", rendered)
        self.assertIn('model = "gpt-example"\n', rendered)
        self.assertIn('model_reasoning_effort = "high"\n', rendered)
        self.assertIn('[plugins."example"]\nenabled = true\n', rendered)
        self.assertEqual(parsed["agents"]["max_threads"], 8)
        self.assertFalse(parsed["agents"]["interrupt_message"])
        for key in MANAGED_TOP_LEVEL_KEYS:
            self.assertEqual(parsed[key], profile[key])

    def test_render_replaces_old_managed_values_and_is_idempotent(self) -> None:
        base = '''model_verbosity = "high"
model_reasoning_summary = "detailed"
tool_output_token_limit = 99
developer_instructions = """
old developer instructions
"""
compact_prompt = ''' + "'''\nold compact prompt\n'''" + '''

[agents]
interrupt_message = true
max_threads = 4
'''
        first = render_promoted_config(PROFILE.read_text(encoding="utf-8"), base)
        second = render_promoted_config(PROFILE.read_text(encoding="utf-8"), first)
        parsed = tomllib.loads(first)

        self.assertEqual(first, second)
        self.assertNotIn("old developer instructions", first)
        self.assertNotIn("old compact prompt", first)
        self.assertEqual(parsed["agents"]["max_threads"], 4)
        self.assertFalse(parsed["agents"]["interrupt_message"])

    def test_promote_creates_verified_backup_and_preserves_mode(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "config.toml"
            backup_root = root / "backups"
            original = 'model = "gpt-example"\n'
            config.write_text(original, encoding="utf-8")
            config.chmod(0o640)

            result = promote_profile(PROFILE, config, backup_root=backup_root)

            self.assertEqual(result.status, "updated")
            self.assertIsNotNone(result.backup)
            assert result.backup is not None
            self.assertEqual(result.backup.read_text(encoding="utf-8"), original)
            self.assertEqual(stat.S_IMODE(config.stat().st_mode), 0o640)
            self.assertEqual(tomllib.loads(config.read_text(encoding="utf-8"))["model"], "gpt-example")

    def test_dry_run_has_no_side_effects(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "config.toml"
            original = 'model = "gpt-example"\n'
            config.write_text(original, encoding="utf-8")

            result = promote_profile(
                PROFILE,
                config,
                dry_run=True,
                backup_root=root / "backups",
            )

            self.assertEqual(result.status, "would-update")
            self.assertEqual(config.read_text(encoding="utf-8"), original)
            self.assertFalse((root / "backups").exists())

    def test_missing_base_config_is_created_private(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "config.toml"
            result = promote_profile(PROFILE, config)

            self.assertEqual(result.status, "installed")
            self.assertEqual(stat.S_IMODE(config.stat().st_mode), 0o600)
            self.assertEqual(
                tomllib.loads(config.read_text(encoding="utf-8"))["model_verbosity"],
                "low",
            )


if __name__ == "__main__":
    unittest.main()
