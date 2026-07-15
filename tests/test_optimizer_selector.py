from __future__ import annotations

import hashlib
import itertools
import json
import os
import subprocess
import sys
import tempfile
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

    def test_all_120_input_combinations_select_only_native_or_v9_lanes(self) -> None:
        dimensions = self.table["dimensions"]
        combinations = itertools.product(
            dimensions["routing_mode"],
            dimensions["task_shape"],
            dimensions["model_family"],
            dimensions["effort"],
        )
        results = [recommend(*values, table=self.table) for values in combinations]
        self.assertEqual(len(results), 120)
        self.assertTrue(
            all(
                result["profile"] is None
                or result["profile"].startswith("smart-compact-v9")
                for result in results
            )
        )
        self.assertEqual(
            {result["skill"] for result in results},
            {None, "smart-compact-v9"},
        )
        self.assertEqual(
            {result["profile"] for result in results},
            {
                None,
                "smart-compact-v9",
                "smart-compact-v9-spark",
                "smart-compact-v9-v8",
            },
        )
        self.assertTrue(
            all(
                result["routingTreatment"]["enforcement"] == "config_before_inference"
                for result in results
            )
        )

    def test_representative_measured_rules(self) -> None:
        cases = {
            ("auto_spark", "implementation", "luna", "max"): "smart-compact-v9-spark",
            ("no_spark", "implementation", "luna", "max"): "smart-compact-v9-v8",
            ("auto_spark", "implementation", "sol", "medium"): "smart-compact-v9-v8",
            ("auto_spark", "migration", "sol", "medium"): None,
            ("auto_spark", "migration", "sol", "high"): "smart-compact-v9-v8",
            ("auto_spark", "handoff", "luna", "xhigh"): "smart-compact-v9",
            ("auto_spark", "handoff", "luna", "max"): "smart-compact-v9-v8",
            ("auto_spark", "general", "luna", "max"): "smart-compact-v9",
        }
        for inputs, expected in cases.items():
            with self.subTest(inputs=inputs):
                self.assertEqual(recommend(*inputs, table=self.table)["profile"], expected)

    def test_rejects_a_legacy_profile_in_the_v9_table(self) -> None:
        drifted = json.loads(json.dumps(self.table))
        drifted["profiles"]["v9"]["profile"] = "smart-compact-v8"
        with self.assertRaisesRegex(ValueError, "native or Smart Compact v9 IDs"):
            recommend("auto_spark", "general", table=drifted)

    def test_v9_profiles_bind_minimal_local_and_explicit_spark_treatments(self) -> None:
        self.assertEqual(
            (ROOT / "profiles" / "smart-compact.config.toml").read_bytes(),
            (ROOT / "profiles" / "smart-compact-v9.config.toml").read_bytes(),
        )
        canonical = (ROOT / "profiles" / "smart-compact-v9.config.toml").read_bytes()
        retired_v8 = (
            ROOT
            / "benchmarks"
            / "retired"
            / "package"
            / "profiles"
            / "smart-compact-v8.config.toml"
        ).read_bytes()
        self.assertNotEqual(canonical, retired_v8)
        self.assertLess(len(canonical), len(retired_v8))
        self.assertEqual(
            (ROOT / "profiles" / "smart-compact-v9-v8.config.toml").read_bytes(),
            retired_v8,
        )
        spark = (ROOT / "profiles" / "smart-compact-v9-spark.config.toml").read_bytes()
        self.assertGreater(len(spark), len(canonical))
        self.assertLessEqual(len(spark), 1_000)

    def test_retired_profiles_are_provenance_only(self) -> None:
        selected = {profile["profile"] for profile in self.table["profiles"].values()}
        for profile_id in self.table["retired_profiles"]:
            with self.subTest(profile=profile_id):
                self.assertNotIn(profile_id, selected)
                self.assertEqual(
                    (ROOT / "profiles" / f"{profile_id}.config.toml").read_bytes(),
                    (
                        ROOT
                        / "benchmarks"
                        / "retired"
                        / "package"
                        / "profiles"
                        / f"{profile_id}.config.toml"
                    ).read_bytes(),
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
            installed = codex_home / "smart-compact-v9.config.toml"
            installed.write_bytes(
                (ROOT / "profiles" / "smart-compact-v9.config.toml").read_bytes()
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
        self.assertEqual(profile.stdout.strip(), "smart-compact-v9")
        self.assertEqual(
            command.stdout.strip(),
            "codex --profile smart-compact-v9 --disable multi_agent",
        )
        self.assertEqual(drifted.returncode, 2)
        self.assertIn("differs from the bound profile", drifted.stderr)
        decoded = json.loads(payload.stdout)
        self.assertEqual(decoded["reasonCode"], "minimal_local_general")
        self.assertEqual(decoded["routingTreatmentName"], "no_spark")

    def test_native_cli_formats_do_not_require_an_installed_profile(self) -> None:
        base = [
            sys.executable,
            str(SCRIPT),
            "--routing-mode",
            "auto_spark",
            "--task-shape",
            "migration",
            "--model-family",
            "sol",
            "--effort",
            "medium",
        ]
        profile = subprocess.run(
            [*base, "--format", "profile"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=True,
        )
        command = subprocess.run(
            [*base, "--format", "command"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=True,
        )
        self.assertEqual(profile.stdout.strip(), "codex-default")
        self.assertEqual(command.stdout.strip(), "codex --disable multi_agent")


if __name__ == "__main__":
    unittest.main()
