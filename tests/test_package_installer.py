from __future__ import annotations

import subprocess
import tempfile
import unittest
from unittest import mock
from pathlib import Path

from scripts.install_smart_compact import activate_plugin, install_marketplace, install_package


ROOT = Path(__file__).parents[1]


class PackageInstallerTests(unittest.TestCase):
    def targets(self, directory: str) -> tuple[Path, Path]:
        root = Path(directory)
        return root / ".agents" / "skills", root / ".codex"

    def test_installs_skill_and_profile(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            skill_root, codex_home = self.targets(directory)
            results = install_package(
                ROOT,
                skill_root,
                codex_home,
                include_spark=False,
            )
            self.assertEqual(
                [result.status for result in results],
                ["installed", "installed", "installed", "installed", "skipped"],
            )
            self.assertEqual(
                (skill_root / "smart-compact" / "SKILL.md").read_text(encoding="utf-8"),
                (ROOT / "SKILL.md").read_text(encoding="utf-8"),
            )
            self.assertTrue((skill_root / "smart-compact" / "agents" / "openai.yaml").is_file())
            self.assertTrue((codex_home / "smart-compact.config.toml").is_file())
            personal_root = skill_root.parent.parent
            self.assertTrue(
                (personal_root / "plugins" / "smart-compact" / ".codex-plugin" / "plugin.json").is_file()
            )
            marketplace = personal_root / ".agents" / "plugins" / "marketplace.json"
            self.assertIn('"name": "smart-compact"', marketplace.read_text(encoding="utf-8"))

    def test_installs_spark_when_available(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            skill_root, codex_home = self.targets(directory)
            results = install_package(
                ROOT,
                skill_root,
                codex_home,
                include_profile=False,
                spark_available=True,
            )
            self.assertEqual(results[-1].status, "installed")
            self.assertTrue((codex_home / "agents" / "spark-worker.toml").is_file())

    def test_skill_conflict_is_non_destructive(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            skill_root, codex_home = self.targets(directory)
            target = skill_root / "smart-compact"
            target.mkdir(parents=True)
            (target / "SKILL.md").write_text("user version\n", encoding="utf-8")
            results = install_package(
                ROOT,
                skill_root,
                codex_home,
                include_profile=False,
                include_plugin=False,
                include_spark=False,
            )
            self.assertEqual(results[0].status, "conflict")
            self.assertEqual((target / "SKILL.md").read_text(encoding="utf-8"), "user version\n")
            self.assertFalse((target / "agents" / "openai.yaml").exists())

    def test_force_replaces_conflicting_skill(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            skill_root, codex_home = self.targets(directory)
            target = skill_root / "smart-compact"
            target.mkdir(parents=True)
            (target / "SKILL.md").write_text("old\n", encoding="utf-8")
            results = install_package(
                ROOT,
                skill_root,
                codex_home,
                force=True,
                include_profile=False,
                include_plugin=False,
                include_spark=False,
            )
            self.assertEqual(results[0].status, "updated")
            self.assertEqual(
                (target / "SKILL.md").read_text(encoding="utf-8"),
                (ROOT / "SKILL.md").read_text(encoding="utf-8"),
            )

    def test_dry_run_changes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            skill_root, codex_home = self.targets(directory)
            results = install_package(
                ROOT,
                skill_root,
                codex_home,
                dry_run=True,
                include_spark=False,
            )
            self.assertEqual(
                [result.status for result in results],
                [
                    "would-install",
                    "would-install",
                    "would-install",
                    "would-install",
                    "skipped",
                ],
            )
            self.assertFalse(skill_root.exists())
            self.assertFalse(codex_home.exists())

    def test_reinstall_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            skill_root, codex_home = self.targets(directory)
            install_package(ROOT, skill_root, codex_home, include_spark=False)
            results = install_package(ROOT, skill_root, codex_home, include_spark=False)
            self.assertEqual(
                [result.status for result in results],
                [
                    "already-installed",
                    "already-installed",
                    "already-installed",
                    "already-installed",
                    "skipped",
                ],
            )

    def test_marketplace_install_preserves_other_plugins(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / ".agents" / "plugins" / "marketplace.json"
            target.parent.mkdir(parents=True)
            target.write_text(
                """{
  "name": "personal",
  "plugins": [
    {
      "name": "existing",
      "source": {"source": "local", "path": "./plugins/existing"},
      "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
      "category": "Productivity"
    }
  ]
}
""",
                encoding="utf-8",
            )

            result = install_marketplace(target, force=False, dry_run=False)

            self.assertEqual(result.status, "installed")
            rendered = target.read_text(encoding="utf-8")
            self.assertIn('"name": "existing"', rendered)
            self.assertIn('"name": "smart-compact"', rendered)

    @mock.patch("scripts.install_smart_compact.shutil.which", return_value="/usr/bin/codex")
    @mock.patch("scripts.install_smart_compact.subprocess.run")
    def test_plugin_activation_uses_personal_marketplace(
        self,
        run: mock.Mock,
        _which: mock.Mock,
    ) -> None:
        run.side_effect = [
            subprocess.CompletedProcess(
                ["codex", "plugin", "marketplace", "list"],
                0,
                "MARKETPLACE ROOT\npersonal /tmp/home\n",
                "",
            ),
            subprocess.CompletedProcess(
                ["codex", "plugin", "add", "smart-compact@personal", "--json"],
                0,
                '{"installed": true}',
                "",
            ),
        ]

        result = activate_plugin("codex", Path("/tmp/home"), 5)

        self.assertEqual(result.status, "installed")
        self.assertEqual(
            run.call_args_list[-1].args[0],
            ["/usr/bin/codex", "plugin", "add", "smart-compact@personal", "--json"],
        )

    def test_make_default_promotes_profile_without_replacing_unrelated_config(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            skill_root, codex_home = self.targets(directory)
            codex_home.mkdir(parents=True)
            config = codex_home / "config.toml"
            config.write_text(
                'model = "gpt-example"\n\n[plugins."example"]\nenabled = true\n',
                encoding="utf-8",
            )

            results = install_package(
                ROOT,
                skill_root,
                codex_home,
                make_default=True,
                include_spark=False,
            )

            default_result = next(
                result for result in results if result.component == "default-profile"
            )
            self.assertEqual(default_result.status, "updated")
            rendered = config.read_text(encoding="utf-8")
            self.assertIn('model = "gpt-example"\n', rendered)
            self.assertIn('[plugins."example"]\nenabled = true\n', rendered)
            self.assertIn('model_verbosity = "low"\n', rendered)

    def test_shell_entrypoint_installs_and_reinstalls(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            skill_root, codex_home = self.targets(directory)
            command = [
                "sh",
                str(ROOT / "install.sh"),
                "--no-spark",
                "--skill-root",
                str(skill_root),
                "--codex-home",
                str(codex_home),
                "--personal-root",
                directory,
                "--codex",
                "codex-command-that-does-not-exist",
            ]

            first = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertTrue((skill_root / "smart-compact" / "SKILL.md").is_file())
            self.assertTrue((codex_home / "smart-compact.config.toml").is_file())
            self.assertTrue(
                (Path(directory) / "plugins" / "smart-compact" / ".codex-plugin" / "plugin.json").is_file()
            )

            second = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertIn("already-installed", second.stdout)


if __name__ == "__main__":
    unittest.main()
