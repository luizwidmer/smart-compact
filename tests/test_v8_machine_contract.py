from __future__ import annotations

import tomllib
import unittest
from pathlib import Path

from scripts.score_policies import projected_calls, safety_score


ROOT = Path(__file__).resolve().parents[1]
V8_SKILL = ROOT / "benchmarks" / "retired" / "package" / "versions" / "v8" / "SKILL.md"
V8_POLICY = ROOT / "benchmarks" / "policies" / "v8" / "SKILL.md"
V8_PROFILE = ROOT / "profiles" / "smart-compact-v8.config.toml"


def machine_contract(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    return text.split("```text\n", 1)[1].split("\n```", 1)[0].strip()


class V8MachineContractTests(unittest.TestCase):
    def test_archived_skill_policy_and_profile_share_one_contract(self) -> None:
        root_contract = machine_contract(V8_SKILL)
        profile = tomllib.loads(V8_PROFILE.read_text(encoding="utf-8"))

        self.assertEqual(machine_contract(V8_POLICY), root_contract)
        self.assertEqual(profile["developer_instructions"].strip(), root_contract)

    def test_contract_is_machine_terse_and_semantically_complete(self) -> None:
        contract = machine_contract(V8_SKILL)
        lines = contract.splitlines()

        self.assertEqual(len(lines), 13)
        self.assertLessEqual(len(contract.encode("utf-8")), 1000)
        self.assertEqual(len({line.split("=", 1)[0] for line in lines}), len(lines))
        for literal in (
            "objective=parent_tokens:min",
            "guard=correctness,safety,scope",
            "acceptance:verbatim_once",
            "preserve=requirements,commands,paths,identifiers,numbers,values,negation,order",
            "workers=smallest_useful;cap:none",
            "brief=partition_ids_first",
            "parent=disjoint_only;consume_accepted_once;drain_all",
            "security_sensitive,destructive,external_state,unverifiable",
            "spark_unavailable=local,no_substitution,no_reprobe",
        ):
            self.assertIn(literal, contract)

        safety, missing = safety_score(contract)
        self.assertEqual((safety, missing), (6, []))
        self.assertLess(projected_calls(contract), 23)

    def test_compaction_contract_is_machine_terse_and_lossless(self) -> None:
        profile = tomllib.loads(V8_PROFILE.read_text(encoding="utf-8"))
        compact = profile["compact_prompt"].strip()

        self.assertEqual(len(compact.splitlines()), 5)
        self.assertLessEqual(len(compact.encode("utf-8")), 500)
        self.assertIn("format=lossless_key_value", compact)
        self.assertIn("accepted_evidence", compact)
        self.assertIn("literals=verbatim", compact)
        self.assertIn("claims=recorded_only", compact)


if __name__ == "__main__":
    unittest.main()
