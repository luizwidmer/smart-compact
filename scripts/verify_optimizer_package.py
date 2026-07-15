#!/usr/bin/env python3
"""Verify Smart Compact v9 provenance and replay its selector over recorded cells."""

from __future__ import annotations

import argparse
import hashlib
import json
import tomllib
from pathlib import Path
from typing import Any

if __package__:
    from .select_optimizer_profile import load_table
    from .benchmark_agentic import write_json_payload
else:
    from select_optimizer_profile import load_table
    from benchmark_agentic import write_json_payload


ROOT = Path(__file__).parents[1]


class VerificationError(RuntimeError):
    """Raised when package evidence or replay totals do not match."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    _require(isinstance(value, dict), f"{path} must contain a JSON object")
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _machine_contract(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    marker = "```text\n"
    _require(marker in text, f"{path} has no machine contract")
    contract = text.split(marker, 1)[1]
    _require("\n```" in contract, f"{path} has an unterminated machine contract")
    return contract.split("\n```", 1)[0]


def verify(root: Path = ROOT) -> dict[str, Any]:
    table = load_table(root / "optimizer" / "selection.json")
    _require(
        (root / "optimizer" / "selection.json").read_bytes()
        == (root / "plugin" / "optimizer" / "selection.json").read_bytes(),
        "package and plugin selection tables differ",
    )
    for source in table["sources"]:
        path = root / source["path"]
        digest = _sha256(path)
        _require(digest == source["sha256"], f"source hash mismatch: {source['path']}")

    profiles = table.get("profiles")
    _require(isinstance(profiles, dict) and profiles, "v9 profile table is empty")
    selected_profile_ids = {
        profile["profile"] for profile in profiles.values() if isinstance(profile.get("profile"), str)
    }
    selected_skill_ids = {
        profile["skill"] for profile in profiles.values() if isinstance(profile.get("skill"), str)
    }
    _require(
        selected_profile_ids
        == {
            "smart-compact-v9",
            "smart-compact-v9-spark",
            "smart-compact-v9-v8",
        },
        "selector exposes a non-v9 profile or omits a v9 lane",
    )
    _require(selected_skill_ids == {"smart-compact-v9"}, "selector exposes a non-v9 skill")
    _require(
        profiles["v9"].get("visibility") == "public"
        and profiles["v9-spark"].get("visibility") == "internal"
        and profiles["v9-v8"].get("visibility") == "internal"
        and profiles["native"].get("profile") is None
        and profiles["native"].get("skill") is None,
        "v9 lane visibility contract drifted",
    )

    versions = sorted(path.parent.name for path in (root / "versions").glob("*/SKILL.md"))
    _require(versions == ["v9"], "only the public v9 version may remain installable")
    _require(
        _machine_contract(root / "SKILL.md")
        == _machine_contract(root / "versions" / "v9" / "SKILL.md"),
        "public smart-compact and smart-compact-v9 skill contracts differ",
    )

    canonical = root / "profiles" / "smart-compact-v9.config.toml"
    unversioned = root / "profiles" / "smart-compact.config.toml"
    spark = root / "profiles" / "smart-compact-v9-spark.config.toml"
    v8_lane = root / "profiles" / "smart-compact-v9-v8.config.toml"
    frozen_canonical = (
        root
        / "benchmarks"
        / "retired"
        / "package"
        / "profiles"
        / "smart-compact-v8.config.toml"
    )
    _require(canonical.read_bytes() == unversioned.read_bytes(), "unversioned v9 alias drifted")
    canonical_config = tomllib.loads(canonical.read_text(encoding="utf-8"))
    canonical_instructions = canonical_config.get("developer_instructions", "")
    _require(
        isinstance(canonical_instructions, str)
        and len(canonical_instructions.encode("utf-8")) <= 300,
        "canonical v9 local contract is not minimal",
    )
    _require("compact_prompt" not in canonical_config, "canonical v9 enforces compact state")
    _require("routing=local;delegation=forbidden" in canonical_instructions, "local route drifted")
    _require(
        canonical.read_bytes() != frozen_canonical.read_bytes(),
        "canonical v9 unexpectedly aliases retired v8",
    )
    _require(
        v8_lane.read_bytes() == frozen_canonical.read_bytes(),
        "internal v9-v8 lane does not preserve the measured frozen profile",
    )
    skill_contract = _machine_contract(root / "versions" / "v9" / "SKILL.md").strip()
    _require(
        "escalate=security,destructive,ambiguous" in skill_contract,
        "v9 skill lost its safety escape line",
    )
    profile_contract = "\n".join(
        line for line in skill_contract.splitlines() if not line.startswith("escalate=")
    )
    _require(
        profile_contract == canonical_instructions.strip(),
        "v9 skill and canonical profile execution contracts differ",
    )
    spark_config = tomllib.loads(spark.read_text(encoding="utf-8"))
    spark_instructions = spark_config.get("developer_instructions", "")
    _require(
        isinstance(spark_instructions, str)
        and len(spark_instructions.encode("utf-8")) <= 800,
        "v9 Spark route is not bounded",
    )
    _require("routing=spark_required" in spark_instructions, "Spark route drifted")
    _require("wait_agent" in spark_instructions, "Spark route does not drain workers")
    _require(spark_config.get("agents", {}).get("interrupt_message") is True, "Spark result delivery disabled")

    retired = table.get("retired_profiles")
    _require(isinstance(retired, list) and retired, "retired profile registry is empty")
    for profile_id in retired:
        _require(profile_id not in selected_profile_ids, f"retired profile is selectable: {profile_id}")
        legacy = root / "profiles" / f"{profile_id}.config.toml"
        archived = (
            root
            / "benchmarks"
            / "retired"
            / "package"
            / "profiles"
            / f"{profile_id}.config.toml"
        )
        _require(legacy.read_bytes() == archived.read_bytes(), f"retired profile drifted: {profile_id}")

    definitive = _load_json(root / "benchmarks" / "results" / "v9-definitive-summary.json")
    _require(
        definitive.get("status") == "v9_definitive_selection_verified"
        and definitive.get("task_correct_cells") == 16,
        "definitive v9 selection evidence is incomplete",
    )
    official = definitive.get("official", {}).get("totals", {})
    fresh = definitive.get("fresh_additions", {}).get("totals", {})
    combined = definitive.get("combined", {})
    uniform = definitive.get("uniform_state_candidate", {})
    _require(
        official.get("v9_parent_tokens") == 2607766
        and official.get("v9_saved_vs_standard") == 530716
        and official.get("v9_saved_vs_v6") == 753338
        and official.get("v9_saved_vs_v8") == 397164
        and official.get("v9_spawned_workers") == 1,
        "official definitive metrics drifted",
    )
    _require(
        fresh.get("v9_parent_tokens") == 462901
        and fresh.get("v9_saved_vs_v8") == 5680,
        "fresh definitive metrics drifted",
    )
    _require(
        combined.get("v9_parent_tokens") == 3070667
        and combined.get("v9_saved_vs_v8") == 402844,
        "combined definitive metrics drifted",
    )
    _require(
        uniform.get("status") == "rejected"
        and uniform.get("parent_tokens") == 3817102
        and uniform.get("state_aware_parent_tokens") == 2607766
        and uniform.get("state_aware_saved_tokens") == 1209336
        and uniform.get("state_aware_reduction_pct") == 31.682,
        "uniform-state cost metrics drifted",
    )
    rejected = _load_json(
        root
        / "benchmarks"
        / "experiments"
        / "v9-official-state-routed-rejected"
        / "result.json"
    )
    _require(
        rejected.get("status") == "rejected_uniform_v9_state_routing"
        and rejected.get("task_correct_cells") == 12,
        "failed uniform-state selection is not disclosed",
    )
    snapshot = rejected.get("frozen_preselection_snapshot", {})
    snapshot_path = snapshot.get("path")
    snapshot_sha = snapshot.get("sha256")
    _require(
        isinstance(snapshot_path, str)
        and isinstance(snapshot_sha, str)
        and _sha256(root / snapshot_path) == snapshot_sha,
        "rejected preselection snapshot is missing or drifted",
    )
    official_freeze = _load_json(root / "benchmarks" / "v9-official-freeze.json")
    _require(
        official_freeze.get("artifacts", {})
        .get("optimizer_selection", {})
        .get("sha256")
        == snapshot_sha,
        "archived preselection does not match the official freeze",
    )
    return {
        "verified": True,
        "product": table["product"],
        "selectableProfiles": sorted(selected_profile_ids),
        "localInstructionBytes": len(canonical_instructions.encode("utf-8")),
        "sparkInstructionBytes": len(spark_instructions.encode("utf-8")),
        "selectionEvidence": {
            "status": definitive["evidence_status"],
            "taskCorrectCells": definitive["task_correct_cells"],
            "official": official,
            "fresh": fresh,
            "combined": combined,
            "selectedOfficialSpawnedWorkers": definitive["selected_official_spawned_workers"],
        },
        "uniformStateCandidate": "rejected",
        "uniformStateCost": uniform,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=None)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = verify()
    if args.output is not None:
        write_json_payload(args.output, report)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
