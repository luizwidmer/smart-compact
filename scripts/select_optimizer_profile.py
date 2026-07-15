#!/usr/bin/env python3
"""Select the evidence-backed Smart Compact v9 lane before task creation."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import sys
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).parents[1]
DEFAULT_TABLE = ROOT / "optimizer" / "selection.json"
V9_PRODUCT = "smart-compact-v9"


class SelectionError(ValueError):
    """Raised when selector inputs or the decision table are invalid."""


def load_table(path: Path = DEFAULT_TABLE) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SelectionError("selection table must be a JSON object")
    if value.get("product") != V9_PRODUCT:
        raise SelectionError(f"selection table product must be {V9_PRODUCT!r}")
    return value


def _allowed(table: Mapping[str, Any], dimension: str) -> tuple[str, ...]:
    dimensions = table.get("dimensions")
    values = dimensions.get(dimension) if isinstance(dimensions, dict) else None
    if not isinstance(values, list) or not values or not all(
        isinstance(value, str) and value for value in values
    ):
        raise SelectionError(f"selection table has invalid dimension {dimension!r}")
    return tuple(values)


def _validate_input(table: Mapping[str, Any], dimension: str, value: str) -> None:
    allowed = _allowed(table, dimension)
    if value not in allowed:
        raise SelectionError(
            f"unsupported {dimension} {value!r}; expected one of {', '.join(allowed)}"
        )


def recommend(
    routing_mode: str,
    task_shape: str,
    model_family: str = "other",
    effort: str = "other",
    *,
    table: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    decision_table = load_table() if table is None else dict(table)
    if decision_table.get("product") != V9_PRODUCT:
        raise SelectionError(f"selection table product must be {V9_PRODUCT!r}")
    inputs = {
        "routing_mode": routing_mode,
        "task_shape": task_shape,
        "model_family": model_family,
        "effort": effort,
    }
    for dimension, value in inputs.items():
        _validate_input(decision_table, dimension, value)

    rules = decision_table.get("rules")
    profiles = decision_table.get("profiles")
    evidence = decision_table.get("evidence")
    treatments = decision_table.get("routing_treatments")
    if not isinstance(rules, list) or not isinstance(profiles, dict):
        raise SelectionError("selection table is missing rules or profiles")
    if not isinstance(evidence, dict) or not isinstance(treatments, dict):
        raise SelectionError("selection table is missing evidence or routing treatments")

    selected: Mapping[str, Any] | None = None
    for rule in rules:
        if not isinstance(rule, dict) or not isinstance(rule.get("when"), dict):
            raise SelectionError("selection table contains an invalid rule")
        if all(inputs.get(key) == value for key, value in rule["when"].items()):
            selected = rule
            break
    if selected is None:
        raise SelectionError("selection table has no matching rule")

    lane = selected.get("lane")
    profile = profiles.get(lane) if isinstance(lane, str) else None
    reason_code = selected.get("reason_code")
    if not isinstance(profile, dict) or not isinstance(reason_code, str):
        raise SelectionError("matching rule references an invalid lane or reason")
    profile_id = profile.get("profile")
    skill = profile.get("skill")
    evidence_text = evidence.get(reason_code)
    treatment_name = selected.get("routing_treatment", routing_mode)
    treatment = treatments.get(treatment_name)
    native = profile_id is None and skill is None
    if not isinstance(evidence_text, str) or not evidence_text:
        raise SelectionError("matching lane has incomplete evidence metadata")
    if not native and not (
        isinstance(profile_id, str)
        and (profile_id == V9_PRODUCT or profile_id.startswith(f"{V9_PRODUCT}-"))
        and skill == V9_PRODUCT
    ):
        raise SelectionError("matching lane must resolve to native or Smart Compact v9 IDs")
    source_path = f"profiles/{profile_id}.config.toml" if not native else None
    profile_source = next(
        (
            source
            for source in decision_table.get("sources", [])
            if isinstance(source, dict) and source.get("path") == source_path
        ),
        None,
    )
    if not isinstance(treatment, dict) or not isinstance(treatment.get("cli_args"), list):
        raise SelectionError("matching route has incomplete treatment metadata")
    if not native and (
        not isinstance(profile_source, dict)
        or not isinstance(profile_source.get("sha256"), str)
    ):
        raise SelectionError("matching lane has no bound profile hash")

    return {
        "schemaVersion": decision_table.get("schema_version"),
        "objective": decision_table.get("objective"),
        "selectionStage": decision_table.get("selection_stage"),
        "inputs": inputs,
        "lane": lane,
        "profile": profile_id,
        "skill": skill,
        "usesNativeDefault": native,
        "reasonCode": reason_code,
        "evidenceTier": selected.get("evidence_tier"),
        "evidence": evidence_text,
        "routingTreatmentName": treatment_name,
        "routingTreatment": treatment,
        "profileSha256": None if native else profile_source["sha256"],
        "cliArgs": (
            ["codex", *treatment["cli_args"]]
            if native
            else ["codex", "--profile", profile_id, *treatment["cli_args"]]
        ),
    }


def build_parser(table: Mapping[str, Any]) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--routing-mode",
        required=True,
        choices=_allowed(table, "routing_mode"),
    )
    parser.add_argument(
        "--task-shape",
        required=True,
        choices=_allowed(table, "task_shape"),
    )
    parser.add_argument(
        "--model-family",
        choices=_allowed(table, "model_family"),
        default="other",
    )
    parser.add_argument(
        "--effort",
        choices=_allowed(table, "effort"),
        default="other",
    )
    parser.add_argument(
        "--format",
        choices=("json", "profile", "command"),
        default="json",
    )
    return parser


def main() -> int:
    table = load_table()
    args = build_parser(table).parse_args()
    result = recommend(
        args.routing_mode,
        args.task_shape,
        args.model_family,
        args.effort,
        table=table,
    )
    if args.format == "json":
        print(json.dumps(result, indent=2, sort_keys=True))
    elif args.format == "profile":
        print(result["profile"] or "codex-default")
    else:
        if not result["usesNativeDefault"]:
            codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
            installed = codex_home / f"{result['profile']}.config.toml"
            if not installed.is_file():
                print(
                    f"Refusing to emit an evidence-backed command: {installed} is not installed.",
                    file=sys.stderr,
                )
                return 2
            digest = hashlib.sha256(installed.read_bytes()).hexdigest()
            if digest != result["profileSha256"]:
                print(
                    f"Refusing to emit an evidence-backed command: {installed} differs from the bound profile.",
                    file=sys.stderr,
                )
                return 2
        print(shlex.join(result["cliArgs"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
