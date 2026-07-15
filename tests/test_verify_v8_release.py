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
    LEGACY_CALCULATOR_CASE,
    LEGACY_RELAY_CASE,
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
        self.legacy_manifest = self.root / "agentic-v8-legacy-calculator.json"
        self.legacy_manifest.write_text(
            json.dumps(
                {
                    "schema_version": 2,
                    "cases": [
                        {
                            "id": LEGACY_CALCULATOR_CASE,
                            "split": "legacy",
                            "delegation": {"mode": "required_when_available"},
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        self.legacy_manifest_sha256 = hashlib.sha256(
            self.legacy_manifest.read_bytes()
        ).hexdigest()
        self.relay_manifest = self.root / "agentic-v8-legacy-relay-bench.json"
        self.relay_manifest.write_text(
            json.dumps(
                {
                    "schema_version": 2,
                    "cases": [
                        {
                            "id": LEGACY_RELAY_CASE,
                            "split": "legacy",
                            "delegation": {"mode": "required_when_available"},
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        self.relay_manifest_sha256 = hashlib.sha256(
            self.relay_manifest.read_bytes()
        ).hexdigest()
        self.hashes = frozen_hashes()
        self.raw_paths = self._write_release_artifacts()
        self.selection_paths: list[Path] = []

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
        if case_id == LEGACY_CALCULATOR_CASE:
            offset = 0
        elif case_id == LEGACY_RELAY_CASE:
            offset = 100
        else:
            offset = self.case_ids.index(case_id) * 10
        return {
            STANDARD_ARM: 1000,
            V6_ARM: 700,
            V8_NO_SPARK_ARM: 650,
            V8_SPARK_FORCED_ARM: 500,
            V8_SPARK_AUTO_ARM: 550,
        }[arm] + offset

    def _result(self, case_id: str, arm: str) -> dict:
        required_spark = arm in V8_SPARK_ARMS and (
            case_id in {LEGACY_CALCULATOR_CASE, LEGACY_RELAY_CASE}
            or case_id in self.required_cases
        )
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

    def _artifact(
        self,
        model: str,
        effort: str,
        cells: list[tuple[str, str]],
        *,
        manifest_sha256: str,
    ) -> dict:
        arms = sorted({arm for _, arm in cells})
        return {
            "schema_version": 3,
            "complete": True,
            "publication_status": {"matrix_complete": True},
            "cases_sha256": manifest_sha256,
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
        expected = expected_release_cells(
            self.case_ids,
            LEGACY_CALCULATOR_CASE,
            LEGACY_RELAY_CASE,
        )
        paths: list[Path] = []
        for case_id, prefix, manifest_sha256 in (
            (LEGACY_CALCULATOR_CASE, "calculator", self.legacy_manifest_sha256),
            (LEGACY_RELAY_CASE, "relay", self.relay_manifest_sha256),
        ):
            for model, effort in SETTINGS:
                cells = sorted(
                    (cell_case_id, arm)
                    for cell_case_id, arm, cell_model, cell_effort in expected
                    if cell_case_id == case_id
                    and (cell_model, cell_effort) == (model, effort)
                )
                path = self.root / f"{prefix}-{model}-{effort}.json"
                path.write_text(
                    json.dumps(
                        self._artifact(
                            model,
                            effort,
                            cells,
                            manifest_sha256=manifest_sha256,
                        )
                    ),
                    encoding="utf-8",
                )
                paths.append(path)
        for model, effort in SETTINGS:
            agentic_cells = sorted(
                (case_id, arm)
                for case_id, arm, cell_model, cell_effort in expected
                if case_id not in {LEGACY_CALCULATOR_CASE, LEGACY_RELAY_CASE}
                and (cell_model, cell_effort) == (model, effort)
            )
            agentic_path = self.root / f"agentic-{model}-{effort}.json"
            agentic_path.write_text(
                json.dumps(
                    self._artifact(
                        model,
                        effort,
                        agentic_cells,
                        manifest_sha256=self.manifest_sha256,
                    )
                ),
                encoding="utf-8",
            )
            paths.append(agentic_path)
        return paths

    def _payload(self, path: Path) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))

    def _save(self, path: Path, payload: dict) -> None:
        path.write_text(json.dumps(payload), encoding="utf-8")

    def _verify(self) -> dict:
        return verify_release(
            self.manifest,
            self.legacy_manifest,
            self.relay_manifest,
            self.raw_paths,
            self.selection_paths,
        )

    def _candidate_payload_and_index(
        self, arm: str = V8_SPARK_AUTO_ARM, *, required: bool = True
    ) -> tuple[Path, dict, int]:
        path = next(
            path
            for path in self.raw_paths
            if (
                path.name.startswith("calculator-")
                if arm == V8_SPARK_FORCED_ARM
                else path.name.startswith("agentic-")
            )
            and path.name.endswith("luna-xhigh.json")
        )
        payload = self._payload(path)
        index = next(
            index
            for index, row in enumerate(payload["results"])
            if row["arm"] == arm
            and (
                required
                if row["case_id"] == LEGACY_CALCULATOR_CASE
                else ((row["case_id"] in self.required_cases) is required)
            )
        )
        return path, payload, index

    def test_exact_21_24_12_9_release_plan(self) -> None:
        cells = expected_release_cells(
            self.case_ids,
            LEGACY_CALCULATOR_CASE,
            LEGACY_RELAY_CASE,
        )
        counts = Counter(cell[1] for cell in cells)
        self.assertEqual(len(cells), 66)
        self.assertEqual(counts[V8_NO_SPARK_ARM], 21)
        self.assertEqual(sum(counts[arm] for arm in CONTROL_ARMS), 24)
        self.assertEqual(counts[V8_SPARK_FORCED_ARM], 12)
        self.assertEqual(counts[V8_SPARK_AUTO_ARM], 9)
        self.assertEqual(
            {cell[0] for cell in cells if cell[1] == V8_SPARK_AUTO_ARM},
            set(self.case_ids) - {MONOREPO_CASE},
        )
        self.assertEqual(
            {
                cell[0]
                for cell in cells
                if cell[1] in (*CONTROL_ARMS, V8_SPARK_FORCED_ARM)
            },
            {LEGACY_CALCULATOR_CASE, LEGACY_RELAY_CASE, MONOREPO_CASE},
        )
        self.assertFalse(any("v7" in cell[1] or cell[1] == LEGACY_SPARK_ARM for cell in cells))

    def test_verifies_tables_routing_and_three_manifest_provenance(self) -> None:
        summary = self._verify()
        self.assertEqual(summary["schema_version"], 3)
        self.assertTrue(summary["verified"])
        self.assertEqual(summary["acceptance_policy"]["hard_gate"], "task_correctness")
        self.assertEqual(summary["acceptance_policy"]["task_correct_cells"], 66)
        self.assertEqual(summary["acceptance_policy"]["protocol_pass_cells"], 66)
        self.assertEqual(summary["release_plan"]["total_cells"], 66)
        self.assertEqual(summary["release_plan"]["tuning_cells_outside_release_verifier"], 6)
        self.assertEqual(summary["release_plan"]["scored_cells_including_tuning"], 72)
        self.assertEqual(summary["release_plan"]["candidate_cells"], 42)
        self.assertEqual(summary["release_plan"]["control_cells"], 24)
        self.assertEqual(summary["release_plan"]["arm_cells"][V8_NO_SPARK_ARM], 21)
        self.assertEqual(summary["release_plan"]["legacy_anchor_cells"], 16)
        self.assertEqual(summary["release_plan"]["relay_anchor_cells"], 16)
        self.assertEqual(summary["release_plan"]["migration_anchor_cells"], 16)
        self.assertEqual(summary["release_plan"]["agentic_non_anchor_cells"], 18)
        coverage = summary["comparative_coverage"]
        self.assertTrue(coverage["fresh_raw_sources"])
        self.assertEqual(coverage["case_universe"], 12)
        self.assertEqual(
            coverage["comparative_case_ids"],
            [LEGACY_CALCULATOR_CASE, LEGACY_RELAY_CASE, MONOREPO_CASE],
        )
        self.assertEqual(
            coverage["standard_v6_v8_scope"],
            "legacy-calculator-legacy-relay-bench-and-monorepo-migration-only",
        )
        self.assertFalse(coverage["suite_wide_standard_v6_v8"])
        self.assertEqual(len(coverage["comparative_cases"]), 3)
        self.assertTrue(
            all(row["standard_v6_v8_complete"] for row in coverage["comparative_cases"])
        )
        self.assertEqual(len(summary["parent_token_table"]), 12)
        self.assertEqual(
            {row["scope"] for row in summary["parent_token_table"]},
            {LEGACY_CALCULATOR_CASE, LEGACY_RELAY_CASE, MONOREPO_CASE},
        )
        self.assertEqual(len(summary["forced_efficacy_table"]), 12)
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
            if row["case_id"] == LEGACY_CALCULATOR_CASE
            and (row["model"], row["effort"]) == PRIMARY_SETTING
        )
        self.assertEqual(primary["no_spark_parent_tokens"], 650)
        self.assertEqual(primary["spark_parent_tokens"], 500)
        self.assertEqual(primary["parent_tokens_saved"], 150)
        self.assertEqual(primary["spawned_workers"], 2)
        self.assertFalse(primary["baseline_reused"])
        self.assertTrue(primary["same_batch"])
        self.assertTrue(primary["wall_time_reportable"])

        self.assertFalse(any(source["retained_selection"] for source in summary["source_artifacts"]))
        self.assertEqual(
            {source["manifest_kind"] for source in summary["source_artifacts"]},
            {
                "agentic-suite",
                "legacy-calculator-anchor",
                "legacy-relay-bench-anchor",
            },
        )

        output = self.root / "summary.json"
        write_summary(output, summary)
        self.assertEqual(json.loads(output.read_text(encoding="utf-8")), summary)
        self.assertTrue(all(path.is_file() for path in self.raw_paths))

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

    def test_rejects_task_and_drain_failures(self) -> None:
        mutations = {
            "task_pass": False,
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
                "scope_ok": False,
            }
        )
        self._save(path, payload)

        summary = self._verify()

        self.assertTrue(summary["verified"])
        self.assertEqual(summary["acceptance_policy"]["task_correct_cells"], 66)
        self.assertEqual(summary["acceptance_policy"]["protocol_pass_cells"], 65)
        self.assertEqual(summary["acceptance_policy"]["rtk_pass_cells"], 65)
        self.assertEqual(summary["acceptance_policy"]["scope_pass_cells"], 65)
        self.assertTrue(
            summary["acceptance_policy"]["protocol_is_disclosed_not_release_blocking"]
        )

    def test_accepts_task_correct_incomplete_child_usage_and_discloses_it(self) -> None:
        path, payload, index = self._candidate_payload_and_index(V8_SPARK_FORCED_ARM)
        row = payload["results"][index]
        child_id = row["child_thread_ids"][0]
        row["usage_complete"] = False
        row["child_usage"][child_id] = None
        known_child_tokens = sum(
            usage["totalTokens"]
            for usage in row["child_usage"].values()
            if usage is not None
        )
        row["child_total_tokens"] = known_child_tokens
        row["combined_total_tokens"] = row["parent_total_tokens"] + known_child_tokens
        self._save(path, payload)

        summary = self._verify()

        self.assertTrue(summary["verified"])
        self.assertEqual(summary["acceptance_policy"]["usage_complete_cells"], 65)
        self.assertEqual(len(summary["acceptance_policy"]["usage_incomplete_cells"]), 1)
        affected = next(
            item
            for item in summary["forced_efficacy_table"]
            if item["case_id"] == LEGACY_CALCULATOR_CASE
            and (item["model"], item["effort"]) == PRIMARY_SETTING
        )
        self.assertFalse(affected["spark_child_usage_complete"])
        self.assertIsNone(affected["spark_child_tokens"])
        self.assertEqual(affected["spark_child_tokens_observed"], known_child_tokens)

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

    def test_binds_each_raw_source_to_its_manifest(self) -> None:
        for prefix, wrong_hash in (
            ("calculator-", self.manifest_sha256),
            ("relay-", self.manifest_sha256),
            ("agentic-", self.legacy_manifest_sha256),
        ):
            with self.subTest(prefix=prefix):
                path = next(path for path in self.raw_paths if path.name.startswith(prefix))
                payload = self._payload(path)
                original = copy.deepcopy(payload)
                payload["cases_sha256"] = wrong_hash
                self._save(path, payload)
                with self.assertRaisesRegex(VerificationError, "case is absent"):
                    self._verify()
                self._save(path, original)

    def test_rejects_retained_selection_for_fresh_additive_release(self) -> None:
        with self.assertRaisesRegex(VerificationError, "fresh raw artifacts"):
            verify_release(
                self.manifest,
                self.legacy_manifest,
                self.relay_manifest,
                self.raw_paths,
                [self.root / "retained-selection.json"],
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

    def test_rejects_non_frozen_legacy_manifests(self) -> None:
        for manifest, expected_id in (
            (self.legacy_manifest, LEGACY_CALCULATOR_CASE),
            (self.relay_manifest, LEGACY_RELAY_CASE),
        ):
            for failure in ("shape", "id", "mode"):
                with self.subTest(manifest=expected_id, failure=failure):
                    payload = self._payload(manifest)
                    original = copy.deepcopy(payload)
                    if failure == "shape":
                        payload["cases"].append(copy.deepcopy(payload["cases"][0]))
                    elif failure == "id":
                        payload["cases"][0]["id"] = MONOREPO_CASE
                    else:
                        payload["cases"][0]["delegation"]["mode"] = "forbidden"
                    self._save(manifest, payload)
                    with self.assertRaises(VerificationError):
                        self._verify()
                    self._save(manifest, original)


if __name__ == "__main__":
    unittest.main()
