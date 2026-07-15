from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from scripts.verify_v8_release import (
    CONTROL_ARMS,
    LEGACY_SPARK_ARM,
    MONOREPO_CASE,
    PRIMARY_SETTING,
    RELEASE_SEED,
    SETTINGS,
    SPARK_AGENT,
    SPARK_MODEL,
    SPARK_ROLE,
    STANDARD_ARM,
    V6_ARM,
    V8_ARMS,
    V8_NO_SPARK_ARM,
    V8_SPARK_ARMS,
    V8_SPARK_AUTO_ARM,
    V8_SPARK_FORCED_ARM,
    VerificationError,
    expected_release_cells,
    frozen_hashes,
    verify_release,
    write_summary,
)


class V8ReleaseVerifierTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.case_ids = [
            MONOREPO_CASE,
            "incident-triage",
            "api-contract-repair",
            "config-migration",
            "heldout-1",
            "heldout-2",
            "heldout-3",
            "heldout-4",
            "heldout-5",
            "heldout-6",
        ]
        self.required_cases = set(self.case_ids[:7])
        cases = [
            {
                "id": case_id,
                "split": "development" if index < 4 else "held-out",
                "delegation": {
                    "mode": (
                        "required_when_available"
                        if case_id in self.required_cases
                        else "forbidden"
                    )
                },
            }
            for index, case_id in enumerate(self.case_ids)
        ]
        self.manifest = self.root / "agentic-v8-confirmation.json"
        self.manifest.write_text(
            json.dumps({"schema_version": 2, "cases": cases}), encoding="utf-8"
        )
        self.manifest_sha256 = hashlib.sha256(self.manifest.read_bytes()).hexdigest()
        self.hashes = frozen_hashes()
        self.raw_paths = self._write_release_artifacts()
        self.selection_paths = [self._write_retained_selection()]

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _metadata(self, arms: list[str]) -> dict[str, dict]:
        flags = {
            STANDARD_ARM: (False, False, False, "none"),
            V6_ARM: (False, False, True, "none"),
            V8_NO_SPARK_ARM: (False, False, False, "none"),
            V8_SPARK_FORCED_ARM: (True, False, False, "forced"),
            V8_SPARK_AUTO_ARM: (True, True, False, "auto"),
        }
        output: dict[str, dict] = {}
        for arm in arms:
            spark, multi_agent, skill_input, routing_mode = flags[arm]
            output[arm] = {
                "spark_enabled": spark,
                "multi_agent": multi_agent,
                "skill_input": skill_input,
                "routing_mode": routing_mode,
                **self.hashes[arm],
            }
        return output

    def _tokens(self, case_id: str, arm: str) -> int:
        offset = self.case_ids.index(case_id) * 10
        return {
            STANDARD_ARM: 1000,
            V6_ARM: 700,
            V8_NO_SPARK_ARM: 650,
            V8_SPARK_FORCED_ARM: 500,
            V8_SPARK_AUTO_ARM: 550,
        }[arm] + offset

    def _result(self, case_id: str, arm: str) -> dict:
        required_spark = arm in V8_SPARK_ARMS and case_id in self.required_cases
        parent_tokens = self._tokens(case_id, arm)
        child_ids = ["worker-1", "worker-2"] if required_spark else []
        child_usage = (
            {"worker-1": {"totalTokens": 40}, "worker-2": {"totalTokens": 60}}
            if required_spark
            else {}
        )
        child_tokens = 100 if required_spark else 0
        origin = (
            "harness_thread" if arm == V8_SPARK_FORCED_ARM else "parent_agent"
        )
        spawn_records = {
            child_id: {
                "model": SPARK_MODEL,
                "origin": origin,
                "prompt": "partition_ids: fixture",
            }
            for child_id in child_ids
        }
        return {
            "case_id": case_id,
            "arm": arm,
            "trial": 1,
            "success": True,
            "task_pass": True,
            "protocol_pass": True,
            "scope_ok": True,
            "acceptance_observed": True,
            "usage_complete": True,
            "rtk_ok": True,
            "routing_ok": True,
            "parent_work_replaced_ok": True,
            "no_active_children": True,
            "all_spawned_workers_useful": True,
            "turn_status": "completed",
            "grade": {"ok": True, "score_pct": 100.0},
            "active_child_ids": [],
            "parent_total_tokens": parent_tokens,
            "child_total_tokens": child_tokens,
            "combined_total_tokens": parent_tokens + child_tokens,
            "parent_usage": {"totalTokens": parent_tokens},
            "child_usage": child_usage,
            "actual_spawned_workers": len(child_ids),
            "useful_worker_count": len(child_ids),
            "child_thread_ids": child_ids,
            "useful_worker_ids": list(child_ids),
            "child_roles": {child_id: SPARK_ROLE for child_id in child_ids},
            "spawn_records": spawn_records,
            "execution_duration_seconds": 100.0 if required_spark else 140.0,
            "first_spawn_seconds": 10.0 if required_spark else None,
            "spawn_delay_pct": 10.0 if required_spark else None,
        }

    def _artifact(self, model: str, effort: str, cells: list[tuple[str, str]]) -> dict:
        arms = sorted({arm for _, arm in cells})
        return {
            "schema_version": 3,
            "complete": True,
            "publication_status": {"matrix_complete": True},
            "cases_sha256": self.manifest_sha256,
            "arms": arms,
            "arm_metadata": self._metadata(arms),
            "spark_agent": (
                {
                    "path": str(SPARK_AGENT),
                    "sha256": hashlib.sha256(SPARK_AGENT.read_bytes()).hexdigest(),
                    "model": SPARK_MODEL,
                }
                if any(arm in V8_SPARK_ARMS for arm in arms)
                else None
            ),
            "model": model,
            "effort": effort,
            "repetitions": 1,
            "jobs": 1,
            "seed": RELEASE_SEED,
            "wall_time_contended": False,
            "results": [self._result(case_id, arm) for case_id, arm in cells],
        }

    def _write_release_artifacts(self) -> list[Path]:
        retained = (MONOREPO_CASE, V8_NO_SPARK_ARM, *PRIMARY_SETTING)
        expected = expected_release_cells(self.case_ids) - {retained}
        paths: list[Path] = []
        for model, effort in SETTINGS:
            cells = sorted(
                (case_id, arm)
                for case_id, arm, cell_model, cell_effort in expected
                if (cell_model, cell_effort) == (model, effort)
            )
            path = self.root / f"{model}-{effort}.json"
            path.write_text(json.dumps(self._artifact(model, effort, cells)), encoding="utf-8")
            paths.append(path)
        return paths

    def _write_retained_selection(self) -> Path:
        selected = self._result(MONOREPO_CASE, V8_NO_SPARK_ARM)
        legacy_metadata = copy.deepcopy(self._metadata([V8_NO_SPARK_ARM])[V8_NO_SPARK_ARM])
        legacy_metadata.pop("routing_mode")
        source_payload = {
            "schema_version": 3,
            "complete": True,
            "publication_status": {
                "matrix_complete": True,
                "candidate_all_pass": False,
                "protocol_publishable": False,
            },
            "cases_sha256": self.manifest_sha256,
            "arms": [V8_NO_SPARK_ARM, LEGACY_SPARK_ARM],
            "arm_metadata": {
                V8_NO_SPARK_ARM: legacy_metadata,
                LEGACY_SPARK_ARM: {
                    "spark_enabled": True,
                    "multi_agent": True,
                    "skill_input": False,
                },
            },
            "spark_agent": {
                "path": str(SPARK_AGENT),
                "sha256": hashlib.sha256(SPARK_AGENT.read_bytes()).hexdigest(),
                "model": SPARK_MODEL,
            },
            "model": PRIMARY_SETTING[0],
            "effort": PRIMARY_SETTING[1],
            "repetitions": 1,
            "jobs": 1,
            "seed": RELEASE_SEED,
            "wall_time_contended": False,
            "results": [
                selected,
                {
                    "case_id": MONOREPO_CASE,
                    "arm": LEGACY_SPARK_ARM,
                    "trial": 1,
                    "success": False,
                    "task_pass": True,
                    "protocol_pass": False,
                },
            ],
        }
        self.retained_source = self.root / "gate5-mixed.json"
        self.retained_source.write_text(json.dumps(source_payload), encoding="utf-8")
        self.retained_source_sha256 = hashlib.sha256(self.retained_source.read_bytes()).hexdigest()
        selection = {
            "schema_version": 1,
            "source_path": self.retained_source.name,
            "source_sha256": self.retained_source_sha256,
            "source_runner_sha256": "b" * 64,
            "no_spark_config_sha256": "c" * 64,
            "selected_cells": [
                {"case_id": MONOREPO_CASE, "arm": V8_NO_SPARK_ARM}
            ],
            "excluded_cells": [
                {
                    "case_id": MONOREPO_CASE,
                    "arm": LEGACY_SPARK_ARM,
                    "reason": "wrong Luna child; exact Spark role gate failed",
                }
            ],
        }
        path = self.root / "retained-selection.json"
        path.write_text(json.dumps(selection), encoding="utf-8")
        return path

    def _payload(self, path: Path) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))

    def _save(self, path: Path, payload: dict) -> None:
        path.write_text(json.dumps(payload), encoding="utf-8")

    def _verify(self) -> dict:
        return verify_release(self.manifest, self.raw_paths, self.selection_paths)

    def _candidate_payload_and_index(
        self, arm: str = V8_SPARK_AUTO_ARM, *, required: bool = True
    ) -> tuple[Path, dict, int]:
        path = next(path for path in self.raw_paths if path.name.endswith("luna-xhigh.json"))
        payload = self._payload(path)
        index = next(
            index
            for index, row in enumerate(payload["results"])
            if row["arm"] == arm
            and ((row["case_id"] in self.required_cases) is required)
        )
        return path, payload, index

    def test_exact_13_8_4_9_release_plan(self) -> None:
        cells = expected_release_cells(self.case_ids)
        counts = Counter(cell[1] for cell in cells)
        self.assertEqual(len(cells), 34)
        self.assertEqual(counts[V8_NO_SPARK_ARM], 13)
        self.assertEqual(sum(counts[arm] for arm in CONTROL_ARMS), 8)
        self.assertEqual(counts[V8_SPARK_FORCED_ARM], 4)
        self.assertEqual(counts[V8_SPARK_AUTO_ARM], 9)
        self.assertEqual(
            {cell[0] for cell in cells if cell[1] == V8_SPARK_AUTO_ARM},
            set(self.case_ids) - {MONOREPO_CASE},
        )
        self.assertFalse(any("v7" in cell[1] or cell[1] == LEGACY_SPARK_ARM for cell in cells))

    def test_verifies_tables_routing_and_retained_provenance(self) -> None:
        summary = self._verify()
        self.assertEqual(summary["schema_version"], 3)
        self.assertTrue(summary["verified"])
        self.assertEqual(summary["acceptance_policy"]["hard_gate"], "task_correctness")
        self.assertEqual(summary["acceptance_policy"]["task_correct_cells"], 34)
        self.assertEqual(summary["acceptance_policy"]["protocol_pass_cells"], 34)
        self.assertEqual(summary["release_plan"]["total_cells"], 34)
        self.assertEqual(summary["release_plan"]["candidate_cells"], 26)
        self.assertEqual(summary["release_plan"]["control_cells"], 8)
        self.assertEqual(summary["release_plan"]["arm_cells"][V8_NO_SPARK_ARM], 13)
        self.assertEqual(len(summary["parent_token_table"]), 4)
        self.assertEqual(len(summary["forced_efficacy_table"]), 4)
        self.assertEqual(len(summary["auto_routing_case_rows"]), 9)
        routing = summary["auto_routing_summary"]
        self.assertEqual(routing["required_cases"], 6)
        self.assertEqual(routing["forbidden_cases"], 3)
        self.assertEqual(routing["required_cases_with_spawn"], 6)
        self.assertEqual(routing["forbidden_cases_quiescent"], 3)
        self.assertEqual(routing["routing_reliability_pct"], 100.0)

        primary = next(
            row
            for row in summary["forced_efficacy_table"]
            if (row["model"], row["effort"]) == PRIMARY_SETTING
        )
        self.assertEqual(primary["no_spark_parent_tokens"], 650)
        self.assertEqual(primary["spark_parent_tokens"], 500)
        self.assertEqual(primary["parent_tokens_saved"], 150)
        self.assertEqual(primary["spawned_workers"], 2)
        self.assertTrue(primary["baseline_reused"])
        self.assertFalse(primary["same_batch"])
        self.assertFalse(primary["wall_time_reportable"])

        retained = next(
            source for source in summary["source_artifacts"] if source["retained_selection"]
        )
        self.assertEqual(retained["sha256"], self.retained_source_sha256)
        self.assertEqual(retained["cells"], 1)
        self.assertEqual(retained["excluded_cells"][0]["arm"], LEGACY_SPARK_ARM)
        self.assertFalse(retained["excluded_cells"][0]["protocol_pass"])
        self.assertEqual(retained["source_runner_sha256"], "b" * 64)
        self.assertEqual(retained["no_spark_config_sha256"], "c" * 64)

        output = self.root / "summary.json"
        write_summary(output, summary)
        self.assertEqual(json.loads(output.read_text(encoding="utf-8")), summary)
        self.assertTrue(all(path.is_file() for path in self.raw_paths))
        self.assertTrue(self.retained_source.is_file())

    def test_rejects_missing_and_duplicate_cells(self) -> None:
        for failure in ("missing", "duplicate"):
            with self.subTest(failure=failure):
                path = self.raw_paths[0]
                payload = self._payload(path)
                original = copy.deepcopy(payload)
                if failure == "missing":
                    payload["results"].pop()
                else:
                    payload["results"].append(copy.deepcopy(payload["results"][0]))
                self._save(path, payload)
                with self.assertRaises(VerificationError):
                    self._verify()
                self._save(path, original)

    def test_rejects_manifest_profile_model_and_agent_mismatches(self) -> None:
        mutations = ("manifest", "profile", "setting", "agent")
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                path = self.raw_paths[0]
                payload = self._payload(path)
                original = copy.deepcopy(payload)
                if mutation == "manifest":
                    payload["cases_sha256"] = "0" * 64
                elif mutation == "profile":
                    payload["arm_metadata"][V8_NO_SPARK_ARM]["profile_sha256"] = "0" * 64
                elif mutation == "setting":
                    payload["model"] = "gpt-5.6-luna"
                    payload["effort"] = "high"
                else:
                    payload["spark_agent"]["sha256"] = "0" * 64
                self._save(path, payload)
                with self.assertRaises(VerificationError):
                    self._verify()
                self._save(path, original)

    def test_rejects_task_usage_and_drain_failures(self) -> None:
        mutations = {
            "task_pass": False,
            "usage_complete": False,
            "no_active_children": False,
        }
        for field, value in mutations.items():
            with self.subTest(field=field):
                path, payload, index = self._candidate_payload_and_index()
                original = copy.deepcopy(payload)
                payload["results"][index][field] = value
                self._save(path, payload)
                with self.assertRaises(VerificationError):
                    self._verify()
                self._save(path, original)

    def test_accepts_task_correct_protocol_failure_and_discloses_it(self) -> None:
        path, payload, index = self._candidate_payload_and_index()
        row = payload["results"][index]
        row.update(
            {
                "success": False,
                "protocol_pass": False,
                "routing_ok": False,
                "parent_work_replaced_ok": False,
                "rtk_ok": False,
            }
        )
        self._save(path, payload)

        summary = self._verify()

        self.assertTrue(summary["verified"])
        self.assertEqual(summary["acceptance_policy"]["task_correct_cells"], 34)
        self.assertEqual(summary["acceptance_policy"]["protocol_pass_cells"], 33)
        self.assertEqual(summary["acceptance_policy"]["rtk_pass_cells"], 33)
        self.assertTrue(
            summary["acceptance_policy"]["protocol_is_disclosed_not_release_blocking"]
        )

    def test_rejects_wrong_role_model_and_origin_for_each_spark_mode(self) -> None:
        for arm, field, value in (
            (V8_SPARK_FORCED_ARM, "role", "default"),
            (V8_SPARK_FORCED_ARM, "model", "gpt-5.6-luna"),
            (V8_SPARK_FORCED_ARM, "origin", "parent_agent"),
            (V8_SPARK_AUTO_ARM, "role", "default"),
            (V8_SPARK_AUTO_ARM, "model", "gpt-5.6-luna"),
            (V8_SPARK_AUTO_ARM, "origin", "harness_thread"),
        ):
            with self.subTest(arm=arm, field=field):
                path, payload, index = self._candidate_payload_and_index(arm)
                original = copy.deepcopy(payload)
                row = payload["results"][index]
                child_id = row["child_thread_ids"][0]
                if field == "role":
                    row["child_roles"][child_id] = value
                else:
                    row["spawn_records"][child_id][field] = value
                self._save(path, payload)
                with self.assertRaises(VerificationError):
                    self._verify()
                self._save(path, original)

    def test_required_routing_must_spawn_and_forbidden_routing_must_not(self) -> None:
        path, payload, required_index = self._candidate_payload_and_index()
        original = copy.deepcopy(payload)
        row = payload["results"][required_index]
        row.update(
            {
                "child_thread_ids": [],
                "useful_worker_ids": [],
                "child_roles": {},
                "spawn_records": {},
                "child_usage": {},
                "child_total_tokens": 0,
                "combined_total_tokens": row["parent_total_tokens"],
                "actual_spawned_workers": 0,
                "useful_worker_count": 0,
                "first_spawn_seconds": None,
            }
        )
        self._save(path, payload)
        with self.assertRaisesRegex(VerificationError, "required-routing case spawned no workers"):
            self._verify()
        self._save(path, original)

        path, payload, forbidden_index = self._candidate_payload_and_index(required=False)
        original = copy.deepcopy(payload)
        payload["results"][forbidden_index] = self._result(
            next(case for case in self.case_ids if case not in self.required_cases),
            V8_SPARK_FORCED_ARM,
        )
        row = payload["results"][forbidden_index]
        row["arm"] = V8_SPARK_AUTO_ARM
        row["actual_spawned_workers"] = 1
        row["useful_worker_count"] = 1
        row["child_thread_ids"] = ["unexpected"]
        row["useful_worker_ids"] = ["unexpected"]
        row["child_roles"] = {"unexpected": SPARK_ROLE}
        row["spawn_records"] = {
            "unexpected": {"model": SPARK_MODEL, "origin": "parent_agent"}
        }
        row["child_usage"] = {"unexpected": {"totalTokens": 10}}
        row["child_total_tokens"] = 10
        row["combined_total_tokens"] = row["parent_total_tokens"] + 10
        row["first_spawn_seconds"] = 1.0
        self._save(path, payload)
        with self.assertRaisesRegex(VerificationError, "forbidden-routing case spawned"):
            self._verify()
        self._save(path, original)

    def test_rejects_control_spawn_and_v7_arm(self) -> None:
        path = self.raw_paths[0]
        for failure in ("control-spawn", "v7"):
            with self.subTest(failure=failure):
                payload = self._payload(path)
                original = copy.deepcopy(payload)
                if failure == "v7":
                    payload["arms"][0] = "v7-spark"
                else:
                    row = next(item for item in payload["results"] if item["arm"] in CONTROL_ARMS)
                    row["actual_spawned_workers"] = 1
                    row["useful_worker_count"] = 1
                    row["child_thread_ids"] = ["unexpected"]
                    row["useful_worker_ids"] = ["unexpected"]
                    row["child_roles"] = {"unexpected": SPARK_ROLE}
                    row["spawn_records"] = {"unexpected": {}}
                    row["child_usage"] = {"unexpected": {"totalTokens": 10}}
                    row["child_total_tokens"] = 10
                    row["combined_total_tokens"] = row["parent_total_tokens"] + 10
                    row["first_spawn_seconds"] = 1.0
                self._save(path, payload)
                with self.assertRaises(VerificationError):
                    self._verify()
                self._save(path, original)

    def test_retained_source_hash_and_complete_classification_are_required(self) -> None:
        original_source = self.retained_source.read_bytes()
        self.retained_source.write_bytes(original_source + b"\n")
        with self.assertRaisesRegex(VerificationError, "retained source hash mismatch"):
            self._verify()
        self.retained_source.write_bytes(original_source)

        descriptor = self.selection_paths[0]
        payload = self._payload(descriptor)
        original = copy.deepcopy(payload)
        payload["excluded_cells"].append(
            {"case_id": "not-in-source", "arm": LEGACY_SPARK_ARM, "reason": "test"}
        )
        self._save(descriptor, payload)
        with self.assertRaisesRegex(VerificationError, "classify every source result"):
            self._verify()
        self._save(descriptor, original)

    def test_retained_source_cannot_also_be_supplied_as_ordinary_raw(self) -> None:
        with self.assertRaisesRegex(VerificationError, "also supplied as ordinary"):
            verify_release(
                self.manifest,
                [*self.raw_paths, self.retained_source],
                self.selection_paths,
            )

    def test_rejects_non_frozen_manifest_shape_and_mode(self) -> None:
        for failure in ("shape", "mode"):
            with self.subTest(failure=failure):
                payload = self._payload(self.manifest)
                original = copy.deepcopy(payload)
                if failure == "shape":
                    payload["cases"].pop()
                else:
                    payload["cases"][0]["delegation"]["mode"] = "optional"
                self._save(self.manifest, payload)
                with self.assertRaises(VerificationError):
                    self._verify()
                self._save(self.manifest, original)


if __name__ == "__main__":
    unittest.main()
