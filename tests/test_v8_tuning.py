import hashlib
import json
import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SUMMARY = ROOT / "benchmarks" / "results" / "v8-tuning-summary.json"
PROFILE = ROOT / "profiles" / "smart-compact-v8.config.toml"


class V8TuningTests(unittest.TestCase):
    def setUp(self) -> None:
        self.summary = json.loads(SUMMARY.read_text())

    def test_all_six_scored_rows_are_green(self) -> None:
        rows = [
            *self.summary["auto_compaction"]["rows"],
            *self.summary["tool_output_limit"]["rows"],
        ]
        self.assertEqual(len(rows), self.summary["completed_scored_runs"])
        self.assertEqual(6, len(rows))
        self.assertTrue(all(row["task_pass"] and row["protocol_pass"] for row in rows))

    def test_each_declared_winner_has_the_fewest_parent_tokens(self) -> None:
        for study in ("auto_compaction", "tool_output_limit"):
            with self.subTest(study=study):
                section = self.summary[study]
                winner = next(row for row in section["rows"] if row["setting"] == section["winner"])
                self.assertEqual(
                    winner["parent_total_tokens"],
                    min(row["parent_total_tokens"] for row in section["rows"]),
                )

    def test_frozen_profile_uses_native_compaction_and_1500_tool_limit(self) -> None:
        data = PROFILE.read_bytes()
        profile = tomllib.loads(data.decode())
        self.assertNotIn("model_auto_compact_token_limit", profile)
        self.assertNotIn("model_auto_compact_token_limit_scope", profile)
        self.assertEqual(profile["tool_output_token_limit"], 1500)
        self.assertEqual(
            hashlib.sha256(data).hexdigest(),
            self.summary["frozen_candidate"]["profile_sha256"],
        )


if __name__ == "__main__":
    unittest.main()
