from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import tomllib
import unittest
from unittest import mock
from pathlib import Path

from scripts.install_smart_compact import (
    activate_plugin,
    build_parser,
    compatibility_skill_from_contents,
    compatibility_skill_contents,
    git_blob_id,
    install_marketplace,
    install_package,
    install_tree,
    retired_skill_contents,
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
            self.assertEqual(
                (skill_root / "smart-compact-v9" / "SKILL.md").read_text(
                    encoding="utf-8"
                ),
                (ROOT / "versions" / "v9" / "SKILL.md").read_text(encoding="utf-8"),
            )
            for version in ("v9", "v9-spark", "v9-v8"):
                self.assertEqual(
                    (codex_home / f"smart-compact-{version}.config.toml").read_text(
                        encoding="utf-8"
                    ),
                    (ROOT / "profiles" / f"smart-compact-{version}.config.toml").read_text(
                        encoding="utf-8"
                    ),
                )
            alias = compatibility_skill_contents(ROOT, "v9")
            self.assertEqual(
                (skill_root / "smart-compact" / "SKILL.md").read_text(encoding="utf-8"),
                alias[Path("SKILL.md")],
            )
            self.assertEqual(
                (codex_home / "smart-compact.config.toml").read_text(encoding="utf-8"),
                (ROOT / "profiles" / "smart-compact-v9.config.toml").read_text(
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
                    (ROOT / "profiles" / "smart-compact-v9.config.toml").read_text(
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
                compatibility_skill_contents(ROOT, "v9")[Path("SKILL.md")],
            )

    def test_known_prior_plugin_blob_upgrades_without_force(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            target = root / "target"
            source.mkdir()
            target.mkdir()
            (source / "server.mjs").write_text("current\n", encoding="utf-8")
            prior = b"prior managed release\n"
            (target / "server.mjs").write_bytes(prior)

            result = install_tree(
                "plugin-source",
                source,
                target,
                force=False,
                dry_run=False,
                managed_blob_ids={Path("server.mjs"): (git_blob_id(prior),)},
            )

            self.assertEqual(result.status, "updated")
            self.assertEqual((target / "server.mjs").read_text(), "current\n")

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

    def test_rejected_v9_implementation_lane_is_archived(self) -> None:
        self.assertEqual(
            (ROOT / "profiles" / "smart-compact-v9-implementation.config.toml").read_bytes(),
            (
                ROOT
                / "benchmarks"
                / "retired"
                / "package"
                / "profiles"
                / "smart-compact-v9-implementation.config.toml"
            ).read_bytes(),
        )

    def test_v9_is_the_only_supported_version(self) -> None:
        self.assertEqual(build_parser().parse_args([]).version, "v9")
        version_action = next(
            action for action in build_parser()._actions if action.dest == "version"
        )
        self.assertEqual(version_action.choices, ("v9",))

    def test_managed_v8_alias_upgrades_to_v9_and_retires_exact_legacy_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            skill_root, codex_home = self.targets(directory)
            retired = ROOT / "benchmarks" / "retired" / "package"
            skill_root.mkdir(parents=True)
            codex_home.mkdir(parents=True)
            shutil.copytree(retired / "versions" / "v8", skill_root / "smart-compact-v8")
            shutil.copytree(retired / "versions" / "v8", skill_root / "smart-compact")
            alias_skill = compatibility_skill_from_contents(
                retired_skill_contents(ROOT, "v8"), "v8"
            )
            for relative, content in alias_skill.items():
                (skill_root / "smart-compact" / relative).write_text(content, encoding="utf-8")
            shutil.copy2(
                retired / "profiles" / "smart-compact-v8.config.toml",
                codex_home / "smart-compact-v8.config.toml",
            )
            shutil.copy2(
                retired / "profiles" / "smart-compact-v8.config.toml",
                codex_home / "smart-compact.config.toml",
            )
            results = install_package(
                ROOT,
                skill_root,
                codex_home,
                include_plugin=False,
                include_spark=False,
            )
            self.assertEqual(
                next(result.status for result in results if result.component == "skill-alias"),
                "updated",
            )
            self.assertEqual(
                next(result.status for result in results if result.component == "profile-alias"),
                "updated",
            )
            self.assertFalse((skill_root / "smart-compact-v8").exists())
            self.assertFalse((codex_home / "smart-compact-v8.config.toml").exists())
            self.assertEqual(
                (codex_home / "smart-compact.config.toml").read_text(encoding="utf-8"),
                (ROOT / "profiles" / "smart-compact-v9.config.toml").read_text(
                    encoding="utf-8"
                ),
            )

    def test_divergent_legacy_installations_are_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            skill_root, codex_home = self.targets(directory)
            legacy_skill = skill_root / "smart-compact-v8"
            legacy_skill.mkdir(parents=True)
            (legacy_skill / "SKILL.md").write_text("user-owned\n", encoding="utf-8")
            codex_home.mkdir(parents=True)
            legacy_profile = codex_home / "smart-compact-v8.config.toml"
            legacy_profile.write_text("user_owned = true\n", encoding="utf-8")

            results = install_package(
                ROOT,
                skill_root,
                codex_home,
                include_plugin=False,
                include_spark=False,
            )

            self.assertEqual(
                next(
                    result.status
                    for result in results
                    if result.component == "retired-skill-v8"
                ),
                "preserved",
            )
            self.assertEqual(
                next(
                    result.status
                    for result in results
                    if result.component == "retired-profile-v8"
                ),
                "preserved",
            )
            self.assertTrue(legacy_skill.exists())
            self.assertEqual(legacy_profile.read_text(encoding="utf-8"), "user_owned = true\n")

    def test_legacy_tree_with_user_empty_directory_is_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            skill_root, codex_home = self.targets(directory)
            retired = ROOT / "benchmarks" / "retired" / "package"
            legacy_skill = skill_root / "smart-compact-v8"
            shutil.copytree(retired / "versions" / "v8", legacy_skill)
            (legacy_skill / "user-empty-directory").mkdir()

            results = install_package(
                ROOT,
                skill_root,
                codex_home,
                include_profile=False,
                include_plugin=False,
                include_spark=False,
            )

            self.assertEqual(
                next(
                    result.status
                    for result in results
                    if result.component == "retired-skill-v8"
                ),
                "preserved",
            )
            self.assertTrue((legacy_skill / "user-empty-directory").is_dir())

    def test_plugin_upgrade_dry_runs_then_retires_exact_legacy_assets(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            skill_root, codex_home = self.targets(directory)
            personal_root = Path(directory)
            retired = ROOT / "benchmarks" / "retired" / "package"
            installed = personal_root / "plugins" / "smart-compact"
            legacy_skill = installed / "skills" / "smart-compact-v8"
            legacy_profile = installed / "profiles" / "smart-compact-v8.config.json"
            shutil.copytree(retired / "versions" / "v8", legacy_skill)
            legacy_profile.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(
                retired / "plugin" / "profiles" / "smart-compact-v8.config.json",
                legacy_profile,
            )

            dry_results = install_package(
                ROOT,
                skill_root,
                codex_home,
                personal_root=personal_root,
                dry_run=True,
                include_profile=False,
                include_spark=False,
            )
            self.assertEqual(
                next(
                    result.status
                    for result in dry_results
                    if result.component == "retired-plugin-skill-v8"
                ),
                "would-retire",
            )
            self.assertTrue(legacy_skill.exists())
            self.assertTrue(legacy_profile.exists())

            results = install_package(
                ROOT,
                skill_root,
                codex_home,
                personal_root=personal_root,
                include_profile=False,
                include_spark=False,
            )
            self.assertEqual(
                next(
                    result.status
                    for result in results
                    if result.component == "retired-plugin-profile-v8"
                ),
                "retired",
            )
            self.assertFalse(legacy_skill.exists())
            self.assertFalse(legacy_profile.exists())

    def test_plugin_bundles_only_v9_product_assets(self) -> None:
        self.assertEqual(
            (ROOT / "plugin" / "skills" / "smart-compact-v9" / "SKILL.md").read_bytes(),
            (ROOT / "versions" / "v9" / "SKILL.md").read_bytes(),
        )
        for version in ("v9", "v9-spark"):
            with self.subTest(version=version):
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
        for retired in ("v6", "v8", "v8-natural"):
            self.assertFalse((ROOT / "plugin" / "skills" / f"smart-compact-{retired}").exists())
            self.assertFalse(
                (ROOT / "plugin" / "profiles" / f"smart-compact-{retired}.config.json").exists()
            )

    def test_active_distribution_has_no_retired_product_ids(self) -> None:
        self.assertEqual(
            sorted(path.name for path in (ROOT / "versions").iterdir() if path.is_dir()),
            ["v9"],
        )
        active_paths = [
            ROOT / "SKILL.md",
            ROOT / "agents" / "openai.yaml",
            *sorted((ROOT / "versions").rglob("*")),
            *sorted((ROOT / "profiles").glob("*")),
            *sorted((ROOT / "plugin" / "skills").rglob("*")),
            *sorted((ROOT / "plugin" / "profiles").glob("*")),
        ]
        retired_ids = ("smart-compact-v6", "smart-compact-v7", "smart-compact-v8")
        for path in active_paths:
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8")
            for retired_id in retired_ids:
                self.assertNotIn(retired_id, text, path)

    def test_installed_plugin_alias_is_v9(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            skill_root, codex_home = self.targets(directory)
            install_package(
                ROOT,
                skill_root,
                codex_home,
                include_profile=False,
                include_spark=False,
            )
            installed = skill_root.parent.parent / "plugins" / "smart-compact"
            self.assertEqual(
                (installed / "skills" / "smart-compact" / "SKILL.md").read_text(
                    encoding="utf-8"
                ),
                compatibility_skill_contents(ROOT, "v9")[Path("SKILL.md")],
            )
            self.assertEqual(
                json.loads(
                    (installed / "profiles" / "smart-compact.config.json").read_text(
                        encoding="utf-8"
                    )
                ),
                tomllib.loads(
                    (ROOT / "profiles" / "smart-compact-v9.config.toml").read_text(
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

    def test_make_default_uses_v9_profile(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            skill_root, codex_home = self.targets(directory)
            results = install_package(
                ROOT,
                skill_root,
                codex_home,
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
                (ROOT / "profiles" / "smart-compact-v9.config.toml").read_text(
                    encoding="utf-8"
                )
            )
            for key, value in selected.items():
                self.assertEqual(promoted[key], value)
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
