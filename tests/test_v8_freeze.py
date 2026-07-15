import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / "benchmarks" / "v8-freeze.json"


def git_blob_id(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode()
    return hashlib.sha1(header + data).hexdigest()


class V8FreezeTests(unittest.TestCase):
    def test_frozen_artifact_hashes_match(self) -> None:
        freeze = json.loads(FREEZE.read_text())
        self.assertEqual(freeze["primary_objective"], "parent_total_tokens")
        self.assertEqual(freeze["release_plan"]["target_scored_runs"], 40)
        self.assertEqual(freeze["release_plan"]["excluded_failed_gate_attempts"], 6)
        self.assertEqual(freeze["release_plan"]["superseded_release_attempts"], 11)
        self.assertEqual(freeze["release_plan"]["excluded_transient_release_attempts"], 1)
        self.assertEqual(freeze["release_plan"]["observed_inference_attempts"], 58)
        self.assertEqual(freeze["release_plan"]["release_matrix_runs"], 34)
        self.assertEqual(freeze["release_plan"]["selected_release_runs"], 34)
        self.assertEqual(freeze["release_plan"]["retained_release_runs"], 3)
        self.assertEqual(freeze["release_plan"]["remaining_release_runs"], 0)
        self.assertEqual(
            freeze["release_plan"]["release_cell_allocation"],
            {
                "v8-no-spark": 13,
                "standard-and-v6-controls": 8,
                "v8-spark-forced": 4,
                "v8-spark-auto": 9,
            },
        )
        self.assertEqual(
            freeze["no_spark_normalized_config_sha256"],
            "8c25d5f2343bb543533fa39f9f00be1a94c89240630140d7e29f52e8000c8616",
        )
        self.assertEqual(freeze["release_plan"]["v7_reruns"], 0)
        self.assertEqual(
            freeze["release_evidence"]["status"],
            "verified_task_correctness_release",
        )
        self.assertEqual(
            freeze["release_evidence"]["acceptance"]["task_correct_cells"],
            34,
        )
        self.assertEqual(
            freeze["release_evidence"]["acceptance"]["protocol_pass_cells"],
            26,
        )

        for name, artifact in freeze["artifacts"].items():
            with self.subTest(name=name):
                data = (ROOT / artifact["path"]).read_bytes()
                self.assertEqual(hashlib.sha256(data).hexdigest(), artifact["sha256"])
                self.assertEqual(git_blob_id(data), artifact["git_blob"])


if __name__ == "__main__":
    unittest.main()
