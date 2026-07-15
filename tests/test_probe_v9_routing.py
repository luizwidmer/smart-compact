from __future__ import annotations

import hashlib
import json
import tomllib
import unittest
from pathlib import Path

from scripts import benchmark_v8, probe_v9_routing, probe_v9_routing_r3


ROOT = Path(__file__).parents[1]
PROFILE = ROOT / "benchmarks" / "experiments" / "v9-routing-probe" / "profile.config.toml"
FREEZE = ROOT / "benchmarks" / "experiments" / "v9-routing-probe" / "freeze.json"
R2_PROFILE = ROOT / "benchmarks" / "experiments" / "v9-routing-probe-r2" / "profile.config.toml"
R2_FREEZE = ROOT / "benchmarks" / "experiments" / "v9-routing-probe-r2" / "freeze.json"
R3_PROFILE = ROOT / "benchmarks" / "experiments" / "v9-routing-probe-r3" / "profile.config.toml"
R3_FREEZE = ROOT / "benchmarks" / "experiments" / "v9-routing-probe-r3" / "freeze.json"


def git_blob_id(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


class V9RoutingProbeTests(unittest.TestCase):
    def test_probe_inputs_are_frozen_before_inference(self) -> None:
        for freeze_path in (FREEZE, R2_FREEZE, R3_FREEZE):
            freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
            self.assertEqual(
                freeze["status"],
                "development_probe_inputs_frozen_before_inference",
            )
            self.assertEqual(freeze["repetitions"], 1)
            self.assertEqual(freeze["jobs"], 1)
            self.assertFalse(freeze["availability_prompt_injected"])
            for artifact in freeze["artifacts"].values():
                data = (ROOT / artifact["path"]).read_bytes()
                self.assertEqual(hashlib.sha256(data).hexdigest(), artifact["sha256"])
                self.assertEqual(git_blob_id(data), artifact["git_blob"])
            prior = freeze.get("prior_observation", freeze.get("prior_probe"))
            self.assertIsNotNone(prior)
            data = (ROOT / prior["path"]).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), prior["sha256"])
            self.assertEqual(git_blob_id(data), prior["git_blob"])

    def test_probe_enables_native_tools_without_availability_prompt(self) -> None:
        profile = tomllib.loads(PROFILE.read_text(encoding="utf-8"))
        spec = probe_v9_routing.configure_probe(PROFILE)
        config = benchmark_v8.build_arm_config(spec, profile)

        self.assertTrue(spec.spark_enabled)
        self.assertTrue(spec.multi_agent)
        self.assertEqual(spec.routing_mode, "none")
        self.assertTrue(config["features"]["multi_agent"])
        self.assertNotIn(
            benchmark_v8.SPARK_AVAILABLE_INSTRUCTION.strip(),
            config["developer_instructions"],
        )

    def test_probe_contract_is_routing_only_and_bounded(self) -> None:
        profile = tomllib.loads(PROFILE.read_text(encoding="utf-8"))
        instructions = profile["developer_instructions"]

        self.assertLessEqual(len(instructions.encode("utf-8")), 650)
        self.assertNotIn("compact_prompt", profile)
        self.assertIn(
            'spawn_agent(agent_type="spark_worker",fork_context=false)',
            instructions,
        )
        self.assertIn("MUST stay local", instructions)
        self.assertIn("Start one; add only disjoint useful workers", instructions)

        r2 = tomllib.loads(R2_PROFILE.read_text(encoding="utf-8"))
        r2_instructions = r2["developer_instructions"]
        self.assertLessEqual(len(r2_instructions.encode("utf-8")), 550)
        self.assertIn("routing=spark_required", r2_instructions)
        self.assertNotIn("MUST stay local", r2_instructions)

        r3 = tomllib.loads(R3_PROFILE.read_text(encoding="utf-8"))
        r3_instructions = r3["developer_instructions"]
        self.assertLessEqual(len(r3_instructions.encode("utf-8")), 600)
        self.assertIn("Worker prompt line 1 MUST be exactly", r3_instructions)
        spec = probe_v9_routing_r3.configure_probe(R3_PROFILE)
        self.assertEqual(spec.routing_mode, "none")
        self.assertTrue(spec.multi_agent)


if __name__ == "__main__":
    unittest.main()
