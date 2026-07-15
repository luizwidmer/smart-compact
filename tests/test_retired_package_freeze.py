from __future__ import annotations

import hashlib
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
EXPECTED_SHA256 = {
    "benchmarks/retired/package/profiles/smart-compact-v6.config.toml": "2efbedb6ff202b724bea6245d97136e6db9d044524eaf0b8ea0c3495df4d3ff7",
    "benchmarks/retired/package/profiles/smart-compact-v7.config.toml": "c264da8147f9f8a1de50b48b6eedab8dc1ada7f30fdf01400b60021639be58ce",
    "benchmarks/retired/package/profiles/smart-compact-v8-natural.config.toml": "478e54b0969bfdef2bd87a9e7ff7bca70d41144813043e17b5af4decec584717",
    "benchmarks/retired/package/profiles/smart-compact-v8.config.toml": "b3e4658e957811c69640351cb2302b759ff0a1811bc83fab5b08dbbf63a4e48c",
    "benchmarks/retired/package/profiles/smart-compact-v9-implementation.config.toml": "2efbedb6ff202b724bea6245d97136e6db9d044524eaf0b8ea0c3495df4d3ff7",
    "benchmarks/retired/package/profiles/smart-compact-v9-natural.config.toml": "478e54b0969bfdef2bd87a9e7ff7bca70d41144813043e17b5af4decec584717",
    "benchmarks/retired/package/versions/v6/SKILL.md": "894faf9672001cc73cee731557c9b71ec860c10489dc55fe717b375050df9c28",
    "benchmarks/retired/package/versions/v6/agents/openai.yaml": "ea0e82bc9d06c2a5c3db866e6d1da075df0ee2a6c9f3ebe68ae060c1b181a860",
    "benchmarks/retired/package/versions/v8/SKILL.md": "a79bbd24d27d032966690878bf1f59948776ff3b61e86c0ff7b07c9b22900031",
    "benchmarks/retired/package/versions/v8/agents/openai.yaml": "3e7df89e815b881bde134a9b38ef391db01c9d33e6b30532652e16a216ba7d6f",
    "benchmarks/retired/package/versions/v8-natural/SKILL.md": "18fc904180986f8a5cc7d0c1681217c1b0ead5f5665caff24d4e1c643086e2f7",
    "benchmarks/retired/package/versions/v8-natural/agents/openai.yaml": "fc5a92d1acd24212490f499c396305458ebbc6c4451a70cfab61f793d6abcab6",
    "benchmarks/retired/package/plugin/profiles/smart-compact-v6.config.json": "33031e489080c07bbcafd0c7af2b6f137e7fcabb14bc6bed2cd6aa68abf42979",
    "benchmarks/retired/package/plugin/profiles/smart-compact-v8.config.json": "5dd7f07ee3a47fa1894ffbc27d0b62385ec16cd4f0d591ff27ab02441c23a36c",
    "benchmarks/retired/package/plugin/profiles/smart-compact-v8-natural.config.json": "c2b6ba5e44b5d4d5ba5c31cea4eb1f64bfe194b43740f89d37d91afc03271c49",
    "benchmarks/retired/package/plugin/profiles/smart-compact-v9-implementation.config.json": "33031e489080c07bbcafd0c7af2b6f137e7fcabb14bc6bed2cd6aa68abf42979",
    "benchmarks/retired/package/plugin/profiles/smart-compact-v9-natural.config.json": "c2b6ba5e44b5d4d5ba5c31cea4eb1f64bfe194b43740f89d37d91afc03271c49",
}


class RetiredPackageFreezeTests(unittest.TestCase):
    def test_retired_upgrade_evidence_is_immutable(self) -> None:
        archived = {
            str(path.relative_to(ROOT))
            for path in (ROOT / "benchmarks" / "retired" / "package").rglob("*")
            if path.is_file()
        }
        self.assertEqual(archived, set(EXPECTED_SHA256))
        for relative, expected in EXPECTED_SHA256.items():
            with self.subTest(path=relative):
                digest = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
                self.assertEqual(digest, expected)


if __name__ == "__main__":
    unittest.main()
