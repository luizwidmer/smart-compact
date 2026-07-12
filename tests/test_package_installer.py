from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.install_smart_compact import install_package


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
            self.assertEqual([result.status for result in results], ["installed", "installed", "skipped"])
            self.assertEqual(
                (skill_root / "codex-compact" / "SKILL.md").read_text(encoding="utf-8"),
                (ROOT / "SKILL.md").read_text(encoding="utf-8"),
            )
            self.assertTrue((skill_root / "codex-compact" / "agents" / "openai.yaml").is_file())
            self.assertTrue((codex_home / "smart-compact.config.toml").is_file())

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
            target = skill_root / "codex-compact"
            target.mkdir(parents=True)
            (target / "SKILL.md").write_text("user version\n", encoding="utf-8")
            results = install_package(
                ROOT,
                skill_root,
                codex_home,
                include_profile=False,
                include_spark=False,
            )
            self.assertEqual(results[0].status, "conflict")
            self.assertEqual((target / "SKILL.md").read_text(encoding="utf-8"), "user version\n")
            self.assertFalse((target / "agents" / "openai.yaml").exists())

    def test_force_replaces_conflicting_skill(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            skill_root, codex_home = self.targets(directory)
            target = skill_root / "codex-compact"
            target.mkdir(parents=True)
            (target / "SKILL.md").write_text("old\n", encoding="utf-8")
            results = install_package(
                ROOT,
                skill_root,
                codex_home,
                force=True,
                include_profile=False,
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
            self.assertEqual([result.status for result in results], ["would-install", "would-install", "skipped"])
            self.assertFalse(skill_root.exists())
            self.assertFalse(codex_home.exists())

    def test_reinstall_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            skill_root, codex_home = self.targets(directory)
            install_package(ROOT, skill_root, codex_home, include_spark=False)
            results = install_package(ROOT, skill_root, codex_home, include_spark=False)
            self.assertEqual(
                [result.status for result in results],
                ["already-installed", "already-installed", "skipped"],
            )

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
            ]

            first = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertTrue((skill_root / "codex-compact" / "SKILL.md").is_file())
            self.assertTrue((codex_home / "smart-compact.config.toml").is_file())

            second = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertIn("already-installed", second.stdout)


if __name__ == "__main__":
    unittest.main()
