from __future__ import annotations

import hashlib
import itertools
import json
import os
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

from scripts.select_optimizer_profile import DEFAULT_TABLE, load_table, recommend


ROOT = Path(__file__).parents[1]
PLUGIN_TABLE = ROOT / "plugin" / "optimizer" / "selection.json"
SCRIPT = ROOT / "scripts" / "select_optimizer_profile.py"


class OptimizerSelectorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.table = load_table()

    def test_plugin_and_package_tables_match(self) -> None:
        self.assertEqual(DEFAULT_TABLE.read_bytes(), PLUGIN_TABLE.read_bytes())

    def test_all_8_input_combinations_select_a_profile_and_treatment(self) -> None:
        dimensions = self.table["dimensions"]
        combinations = itertools.product(
            dimensions["routing_mode"],
            dimensions["task_shape"],
        )
        results = [recommend(*values, table=self.table) for values in combinations]
        self.assertEqual(len(results), 8)
        self.assertTrue(all(result["profile"].startswith("smart-compact-") for result in results))
        self.assertTrue(
            all(
                result["routingTreatment"]["enforcement"] == "config_before_inference"
                for result in results
            )
        )

    def test_representative_measured_rules(self) -> None:
        cases = {
            ("auto_spark", "general"): "smart-compact-v8",
            ("auto_spark", "implementation"): "smart-compact-v8",
            ("no_spark", "implementation"): "smart-compact-v6",
            ("no_spark", "migration"): "smart-compact-v8-natural",
            ("no_spark", "handoff"): "smart-compact-v8-natural",
            ("no_spark", "general"): "smart-compact-v8-natural",
        }
        for inputs, expected in cases.items():
            with self.subTest(inputs=inputs):
                self.assertEqual(recommend(*inputs, table=self.table)["profile"], expected)

    def test_natural_profile_is_exact_frozen_treatment(self) -> None:
        installed = ROOT / "profiles" / "smart-compact-v8-natural.config.toml"
        frozen = ROOT / "benchmarks" / "experiments" / "v8-verbose" / "profile.config.toml"
        self.assertEqual(installed.read_bytes(), frozen.read_bytes())
        self.assertEqual(
            tomllib.loads(installed.read_text(encoding="utf-8")),
            json.loads(
                (ROOT / "plugin" / "profiles" / "smart-compact-v8-natural.config.json").read_text(
                    encoding="utf-8"
                )
            ),
        )
        packaged_skill = (ROOT / "versions" / "v8-natural" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        frozen_skill = (
            ROOT / "benchmarks" / "experiments" / "v8-verbose" / "SKILL.md"
        ).read_text(encoding="utf-8")
        self.assertEqual(
            packaged_skill.split("## Instructions\n", 1)[1],
            frozen_skill.split("## Instructions\n", 1)[1],
        )

    def test_source_hashes_are_bound(self) -> None:
        for source in self.table["sources"]:
            digest = hashlib.sha256((ROOT / source["path"]).read_bytes()).hexdigest()
            self.assertEqual(digest, source["sha256"], source["path"])

    def test_cli_formats(self) -> None:
        base = [
            sys.executable,
            str(SCRIPT),
            "--routing-mode",
            "auto_spark",
            "--task-shape",
            "general",
        ]
        profile = subprocess.run(
            [*base, "--format", "profile"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=True,
        )
        payload = subprocess.run(
            [*base, "--format", "json"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=True,
        )
        with tempfile.TemporaryDirectory() as directory:
            codex_home = Path(directory)
            installed = codex_home / "smart-compact-v8.config.toml"
            installed.write_bytes(
                (ROOT / "profiles" / "smart-compact-v8.config.toml").read_bytes()
            )
            environment = {**os.environ, "CODEX_HOME": str(codex_home)}
            command = subprocess.run(
                [*base, "--format", "command"],
                cwd=ROOT,
                env=environment,
                text=True,
                capture_output=True,
                check=True,
            )
            installed.write_text("developer_instructions = 'drift'\n", encoding="utf-8")
            drifted = subprocess.run(
                [*base, "--format", "command"],
                cwd=ROOT,
                env=environment,
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertEqual(profile.stdout.strip(), "smart-compact-v8")
        self.assertEqual(
            command.stdout.strip(),
            "codex --profile smart-compact-v8 --enable multi_agent",
        )
        self.assertEqual(drifted.returncode, 2)
        self.assertIn("differs from the bound profile", drifted.stderr)
        self.assertEqual(json.loads(payload.stdout)["reasonCode"], "auto_aggregate_terse")


if __name__ == "__main__":
    unittest.main()
