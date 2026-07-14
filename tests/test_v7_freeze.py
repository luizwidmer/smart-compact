import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / "benchmarks" / "v7-freeze.json"


def git_blob_id(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode()
    return hashlib.sha1(header + data).hexdigest()


class V7FreezeTests(unittest.TestCase):
    def test_frozen_artifact_hashes_match(self) -> None:
        freeze = json.loads(FREEZE.read_text())
        self.assertEqual(
            freeze["primary_objective"],
            "parent_tokens_saved_per_spawned_worker",
        )

        for name, artifact in freeze["artifacts"].items():
            with self.subTest(name=name):
                data = (ROOT / artifact["path"]).read_bytes()
                self.assertEqual(hashlib.sha256(data).hexdigest(), artifact["sha256"])
                self.assertEqual(git_blob_id(data), artifact["git_blob"])


if __name__ == "__main__":
    unittest.main()
