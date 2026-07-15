from __future__ import annotations

import json
import subprocess
import tempfile
import tomllib
import unittest
from unittest import mock
from pathlib import Path

from scripts.install_smart_compact import (
    activate_plugin,
    build_parser,
    compatibility_skill_contents,
    install_marketplace,
    install_package,
)


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
                ["installed"] * 8 + ["skipped"],
            )
            for version in ("v6", "v8"):
                self.assertEqual(
                    (skill_root / f"smart-compact-{version}" / "SKILL.md").read_text(
                        encoding="utf-8"
                    ),
                    (ROOT / "versions" / version / "SKILL.md").read_text(encoding="utf-8"),
                )
                self.assertEqual(
                    (codex_home / f"smart-compact-{version}.config.toml").read_text(
                        encoding="utf-8"
                    ),
                    (ROOT / "profiles" / f"smart-compact-{version}.config.toml").read_text(
                        encoding="utf-8"
                    ),
                )
            alias = compatibility_skill_contents(ROOT, "v8")
            self.assertEqual(
                (skill_root / "smart-compact" / "SKILL.md").read_text(encoding="utf-8"),
                alias[Path("SKILL.md")],
            )
            self.assertEqual(
                (codex_home / "smart-compact.config.toml").read_text(encoding="utf-8"),
                (ROOT / "profiles" / "smart-compact-v8.config.toml").read_text(
                    encoding="utf-8"
                ),
            )
            personal_root = skill_root.parent.parent
            self.assertTrue(
                (personal_root / "plugins" / "smart-compact" / ".codex-plugin" / "plugin.json").is_file()
            )
            installed_plugin = personal_root / "plugins" / "smart-compact"
            self.assertEqual(
                (installed_plugin / "skills" / "smart-compact" / "SKILL.md").read_text(
                    encoding="utf-8"
                ),
                alias[Path("SKILL.md")],
            )
            self.assertEqual(
                json.loads(
                    (installed_plugin / "profiles" / "smart-compact.config.json").read_text(
                        encoding="utf-8"
                    )
                ),
                tomllib.loads(
                    (ROOT / "profiles" / "smart-compact-v8.config.toml").read_text(
                        encoding="utf-8"
                    )
                ),
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
            alias_result = next(result for result in results if result.component == "skill-alias")
            self.assertEqual(alias_result.status, "conflict")
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
            alias_result = next(result for result in results if result.component == "skill-alias")
            self.assertEqual(alias_result.status, "updated")
            self.assertEqual(
                (target / "SKILL.md").read_text(encoding="utf-8"),
                compatibility_skill_contents(ROOT, "v8")[Path("SKILL.md")],
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
                ["would-install"] * 8 + ["skipped"],
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
                ["already-installed"] * 8 + ["skipped"],
            )

    def test_v6_profile_is_the_frozen_benchmark_profile(self) -> None:
        self.assertEqual(
            (ROOT / "profiles" / "smart-compact-v6.config.toml").read_bytes(),
            (ROOT / "benchmarks" / "profiles" / "v6.config.toml").read_bytes(),
        )

    def test_default_version_is_v8(self) -> None:
        self.assertEqual(build_parser().parse_args([]).version, "v8")

    def test_selected_alias_switches_between_managed_versions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            skill_root, codex_home = self.targets(directory)
            install_package(
                ROOT,
                skill_root,
                codex_home,
                version="v6",
                include_plugin=False,
                include_spark=False,
            )
            self.assertEqual(
                (skill_root / "smart-compact" / "SKILL.md").read_text(encoding="utf-8"),
                compatibility_skill_contents(ROOT, "v6")[Path("SKILL.md")],
            )
            self.assertEqual(
                (codex_home / "smart-compact.config.toml").read_text(encoding="utf-8"),
                (ROOT / "profiles" / "smart-compact-v6.config.toml").read_text(
                    encoding="utf-8"
                ),
            )

            results = install_package(
                ROOT,
                skill_root,
                codex_home,
                version="v8",
                include_plugin=False,
                include_spark=False,
            )

            self.assertEqual(
                next(
                    result.status for result in results if result.component == "skill-alias"
                ),
                "updated",
            )
            self.assertEqual(
                next(
                    result.status for result in results if result.component == "profile-alias"
                ),
                "updated",
            )
            self.assertEqual(
                (codex_home / "smart-compact.config.toml").read_text(encoding="utf-8"),
                (ROOT / "profiles" / "smart-compact-v8.config.toml").read_text(
                    encoding="utf-8"
                ),
            )

    def test_plugin_bundles_both_versioned_skills_and_profiles(self) -> None:
        for version in ("v6", "v8"):
            with self.subTest(version=version):
                self.assertEqual(
                    (
                        ROOT
                        / "plugin"
                        / "skills"
                        / f"smart-compact-{version}"
                        / "SKILL.md"
                    ).read_bytes(),
                    (ROOT / "versions" / version / "SKILL.md").read_bytes(),
                )
                self.assertEqual(
                    (
                        ROOT
                        / "plugin"
                        / "skills"
                        / f"smart-compact-{version}"
                        / "agents"
                        / "openai.yaml"
                    ).read_bytes(),
                    (ROOT / "versions" / version / "agents" / "openai.yaml").read_bytes(),
                )
                native = tomllib.loads(
                    (
                        ROOT / "profiles" / f"smart-compact-{version}.config.toml"
                    ).read_text(encoding="utf-8")
                )
                bundled = json.loads(
                    (
                        ROOT
                        / "plugin"
                        / "profiles"
                        / f"smart-compact-{version}.config.json"
                    ).read_text(encoding="utf-8")
                )
                self.assertEqual(bundled, native)

    def test_installed_plugin_alias_follows_v6_selection(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            skill_root, codex_home = self.targets(directory)
            install_package(
                ROOT,
                skill_root,
                codex_home,
                version="v6",
                include_profile=False,
                include_spark=False,
            )
            installed = skill_root.parent.parent / "plugins" / "smart-compact"
            self.assertEqual(
                (installed / "skills" / "smart-compact" / "SKILL.md").read_text(
                    encoding="utf-8"
                ),
                compatibility_skill_contents(ROOT, "v6")[Path("SKILL.md")],
            )
            self.assertEqual(
                json.loads(
                    (installed / "profiles" / "smart-compact.config.json").read_text(
                        encoding="utf-8"
                    )
                ),
                tomllib.loads(
                    (ROOT / "profiles" / "smart-compact-v6.config.toml").read_text(
                        encoding="utf-8"
                    )
                ),
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

    def test_make_default_uses_selected_v6_profile(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            skill_root, codex_home = self.targets(directory)
            results = install_package(
                ROOT,
                skill_root,
                codex_home,
                version="v6",
                make_default=True,
                include_plugin=False,
                include_spark=False,
            )

            default_result = next(
                result for result in results if result.component == "default-profile"
            )
            self.assertEqual(default_result.status, "installed")
            promoted = tomllib.loads(
                (codex_home / "config.toml").read_text(encoding="utf-8")
            )
            selected = tomllib.loads(
                (ROOT / "profiles" / "smart-compact-v6.config.toml").read_text(
                    encoding="utf-8"
                )
            )
            for key, value in selected.items():
                self.assertEqual(promoted[key], value)
            self.assertNotIn("personality", promoted)
            self.assertNotIn("model_auto_compact_token_limit", promoted)

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
