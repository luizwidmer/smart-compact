from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.verify_v8_release import V8_ARMS, V8_SPARK_ARMS, VerificationError
from scripts.verify_v8_verbose_experiment import (
    DEFAULT_LEGACY_MANIFEST,
    DEFAULT_MANIFEST,
    DEFAULT_RELAY_MANIFEST,
    DEFAULT_RELEASE_SUMMARY,
    ROOT,
    expected_verbose_cells,
    verify_verbose_experiment,
)


class V8VerboseExperimentVerifierTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.profile = self.root / "verbose-profile.toml"
        self.policy = self.root / "SKILL.md"
        self.profile.write_text("developer_instructions = \"verbose\"\n", encoding="utf-8")
        self.policy.write_text("# Verbose policy\n", encoding="utf-8")
        self.raws = self._verbose_artifacts()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    @staticmethod
    def _source_path(value: str) -> Path:
        path = Path(value)
        return path if path.is_absolute() else ROOT / path

    def _verbose_artifacts(self) -> list[Path]:
        release = json.loads(DEFAULT_RELEASE_SUMMARY.read_text(encoding="utf-8"))
        profile_sha = hashlib.sha256(self.profile.read_bytes()).hexdigest()
        policy_sha = hashlib.sha256(self.policy.read_bytes()).hexdigest()
        outputs: list[Path] = []
        for index, source in enumerate(release["source_artifacts"]):
            payload = json.loads(self._source_path(source["path"]).read_text(encoding="utf-8"))
            payload["arms"] = [arm for arm in payload["arms"] if arm in V8_ARMS]
            payload["arm_metadata"] = {
                arm: copy.deepcopy(payload["arm_metadata"][arm]) for arm in payload["arms"]
            }
            for metadata in payload["arm_metadata"].values():
                metadata["profile_sha256"] = profile_sha
                metadata["policy_sha256"] = policy_sha
            payload["results"] = [
                copy.deepcopy(result) for result in payload["results"] if result["arm"] in V8_ARMS
            ]
            for result in payload["results"]:
                result["parent_total_tokens"] -= 1
                if result["combined_total_tokens"] is not None:
                    result["combined_total_tokens"] -= 1
                result["parent_usage"]["totalTokens"] -= 1
            path = self.root / f"verbose-{index}.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            outputs.append(path)
        return outputs

    def _verify(self):
        return verify_verbose_experiment(
            manifest=DEFAULT_MANIFEST,
            legacy_manifest=DEFAULT_LEGACY_MANIFEST,
            relay_manifest=DEFAULT_RELAY_MANIFEST,
            verbose_profile=self.profile,
            verbose_policy=self.policy,
            verbose_raw_artifacts=self.raws,
            release_summary=DEFAULT_RELEASE_SUMMARY,
        )

    def test_exact_42_cell_comparison_and_parent_aggregate(self) -> None:
        summary = self._verify()
        self.assertTrue(summary["verified"])
        self.assertEqual(summary["coverage"]["planned_invocations"], 13)
        self.assertEqual(summary["coverage"]["verbose_artifacts"], 13)
        self.assertEqual(summary["coverage"]["verbose_cells"], 42)
        self.assertEqual(summary["coverage"]["mechy_cells"], 42)
        self.assertEqual(summary["coverage"]["excluded_failed_attempts"], 0)
        self.assertEqual(len(summary["comparisons"]), 42)
        self.assertEqual(summary["primary_parent_token_aggregate"]["parent_tokens_saved"], 42)
        self.assertFalse(summary["disclosures"]["wall_time"]["publishable"])

    def test_rejects_missing_verbose_artifact(self) -> None:
        self.raws.pop()
        with self.assertRaisesRegex(VerificationError, "at least the 13"):
            self._verify()

    def test_rejects_task_failure(self) -> None:
        payload = json.loads(self.raws[0].read_text(encoding="utf-8"))
        payload["results"][0]["task_pass"] = False
        self.raws[0].write_text(json.dumps(payload), encoding="utf-8")
        with self.assertRaisesRegex(VerificationError, "failed attempt has a passing grade"):
            self._verify()

    def test_rejects_treatment_miss(self) -> None:
        for path in self.raws:
            payload = json.loads(path.read_text(encoding="utf-8"))
            target = next((row for row in payload["results"] if row["arm"] in V8_SPARK_ARMS), None)
            if target is None:
                continue
            target["actual_spawned_workers"] = 0
            target["useful_worker_count"] = 0
            target["child_thread_ids"] = []
            target["useful_worker_ids"] = []
            target["child_roles"] = {}
            target["spawn_records"] = {}
            target["child_usage"] = {}
            target["child_total_tokens"] = 0
            target["combined_total_tokens"] = target["parent_total_tokens"]
            path.write_text(json.dumps(payload), encoding="utf-8")
            break
        with self.assertRaisesRegex(VerificationError, "required Spark treatment did not spawn"):
            self._verify()

    def test_allows_and_discloses_incomplete_child_usage(self) -> None:
        initial_incomplete = len(self._verify()["disclosures"]["incomplete_child_usage"])
        for path in self.raws:
            payload = json.loads(path.read_text(encoding="utf-8"))
            target = next(
                (
                    row
                    for row in payload["results"]
                    if row["arm"] in V8_SPARK_ARMS and row["usage_complete"]
                ),
                None,
            )
            if target is None:
                continue
            target["usage_complete"] = False
            target["child_total_tokens"] = None
            target["combined_total_tokens"] = None
            first_child = target["child_thread_ids"][0]
            target["child_usage"][first_child] = None
            path.write_text(json.dumps(payload), encoding="utf-8")
            break
        summary = self._verify()
        self.assertEqual(
            len(summary["disclosures"]["incomplete_child_usage"]),
            initial_incomplete + 1,
        )
        self.assertIsNone(summary["primary_parent_token_aggregate"]["verbose_child_tokens"])

    def test_selects_single_targeted_retry_and_discloses_failed_attempt(self) -> None:
        path = next(
            path
            for path in self.raws
            if any(
                row["arm"] in V8_SPARK_ARMS
                for row in json.loads(path.read_text(encoding="utf-8"))["results"]
            )
        )
        payload = json.loads(path.read_text(encoding="utf-8"))
        index = next(
            index
            for index, row in enumerate(payload["results"])
            if row["arm"] in V8_SPARK_ARMS
        )
        accepted = copy.deepcopy(payload["results"][index])
        payload["results"][index]["task_pass"] = False
        payload["results"][index]["protocol_pass"] = False
        payload["results"][index]["success"] = False
        payload["results"][index]["grade"] = {
            "ok": False,
            "score_pct": 0.0,
            "passed": 0,
            "total": 1,
            "checks": [],
        }
        path.write_text(json.dumps(payload), encoding="utf-8")

        retry = copy.deepcopy(payload)
        retry["arms"] = [accepted["arm"]]
        retry["arm_metadata"] = {
            accepted["arm"]: retry["arm_metadata"][accepted["arm"]]
        }
        retry["results"] = [accepted]
        retry_path = self.root / "verbose-targeted-retry.json"
        retry_path.write_text(json.dumps(retry), encoding="utf-8")
        self.raws.append(retry_path)

        summary = self._verify()

        self.assertEqual(summary["coverage"]["verbose_source_artifacts"], 14)
        self.assertEqual(summary["coverage"]["excluded_failed_attempts"], 1)
        self.assertEqual(len(summary["disclosures"]["excluded_failed_attempts"]), 1)
        self.assertEqual(summary["hard_gates"]["task_correctness"], "42/42")

    def test_expected_verbose_matrix_has_required_arm_counts(self) -> None:
        manifest = json.loads(DEFAULT_MANIFEST.read_text(encoding="utf-8"))
        cells = expected_verbose_cells([case["id"] for case in manifest["cases"]])
        counts = {arm: sum(cell[1] == arm for cell in cells) for arm in V8_ARMS}
        self.assertEqual(counts, {"v8-no-spark": 21, "v8-spark-forced": 12, "v8-spark-auto": 9})


if __name__ == "__main__":
    unittest.main()
