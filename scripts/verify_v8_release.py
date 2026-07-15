#!/usr/bin/env python3
"""Verify and summarize the frozen Smart Compact v8 release matrix.

The verifier is intentionally read-only with respect to raw benchmark artifacts.  It
binds every result to its frozen agentic or legacy manifest, profiles, and policies
before recomputing the publication tables from the individual result rows.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).parents[1]
DEFAULT_MANIFEST = ROOT / "benchmarks" / "agentic-v8-confirmation.json"
DEFAULT_LEGACY_MANIFEST = ROOT / "benchmarks" / "agentic-v8-legacy-calculator.json"
DEFAULT_RELAY_MANIFEST = ROOT / "benchmarks" / "agentic-v8-legacy-relay-bench.json"
V6_PROFILE = ROOT / "benchmarks" / "profiles" / "v6.config.toml"
V6_POLICY = ROOT / "benchmarks" / "policies" / "v6" / "SKILL.md"
V8_PROFILE = ROOT / "profiles" / "smart-compact-v8.config.toml"
V8_POLICY = ROOT / "benchmarks" / "policies" / "v8" / "SKILL.md"
SPARK_AGENT = ROOT / ".codex" / "agents" / "spark-worker.toml"

RELEASE_SEED = 20260721
MONOREPO_CASE = "monorepo-sdk-migration"
LEGACY_CALCULATOR_CASE = "legacy-calculator"
LEGACY_RELAY_CASE = "legacy-relay-bench"
STANDARD_ARM = "standard-no-spark"
V6_ARM = "v6-no-spark"
V8_NO_SPARK_ARM = "v8-no-spark"
V8_SPARK_FORCED_ARM = "v8-spark-forced"
V8_SPARK_AUTO_ARM = "v8-spark-auto"
LEGACY_SPARK_ARM = "v8-spark"
SPARK_MODEL = "gpt-5.3-codex-spark"
SPARK_ROLE = "spark_worker"
KNOWN_ARMS = (
    STANDARD_ARM,
    V6_ARM,
    V8_NO_SPARK_ARM,
    V8_SPARK_FORCED_ARM,
    V8_SPARK_AUTO_ARM,
)
V8_SPARK_ARMS = (V8_SPARK_FORCED_ARM, V8_SPARK_AUTO_ARM)
V8_ARMS = (V8_NO_SPARK_ARM, *V8_SPARK_ARMS)
CONTROL_ARMS = (STANDARD_ARM, V6_ARM)
SETTINGS = (
    ("gpt-5.6-sol", "medium"),
    ("gpt-5.6-sol", "high"),
    ("gpt-5.6-luna", "xhigh"),
    ("gpt-5.6-luna", "max"),
)
PRIMARY_SETTING = ("gpt-5.6-luna", "xhigh")


class VerificationError(ValueError):
    """Raised when one or more release invariants are violated."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _display_path(path: Path) -> str:
    """Return repository-relative paths so committed summaries are portable."""
    resolved = path.expanduser().resolve()
    try:
        return str(resolved.relative_to(ROOT))
    except ValueError:
        return str(resolved)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def _is_int(value: object) -> bool:
    return type(value) is int


def _percentage(baseline: int | float, candidate: int | float) -> float:
    _require(baseline > 0, "token baseline must be positive")
    return round((baseline - candidate) / baseline * 100, 3)


def load_release_manifest(path: Path) -> tuple[list[str], dict[str, str], str]:
    resolved = path.expanduser().resolve()
    _require(resolved.is_file(), f"confirmation manifest not found: {resolved}")
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise VerificationError(f"cannot read confirmation manifest: {error}") from error
    _require(isinstance(payload, dict), "confirmation manifest must be an object")
    _require(payload.get("schema_version") == 2, "confirmation manifest must use schema 2")
    cases = payload.get("cases")
    _require(isinstance(cases, list), "confirmation manifest cases must be a list")
    _require(len(cases) == 10, "v8 confirmation manifest must contain exactly 10 cases")
    ids: list[str] = []
    delegation_modes: dict[str, str] = {}
    splits: Counter[str] = Counter()
    for index, case in enumerate(cases):
        _require(isinstance(case, dict), f"manifest case {index} must be an object")
        case_id = case.get("id")
        split = case.get("split")
        delegation = case.get("delegation")
        _require(isinstance(case_id, str) and bool(case_id), f"manifest case {index} has no id")
        _require(split in {"development", "held-out"}, f"invalid split for {case_id}")
        _require(isinstance(delegation, dict), f"missing delegation contract for {case_id}")
        mode = delegation.get("mode")
        _require(
            mode in {"required_when_available", "forbidden"},
            f"invalid delegation mode for {case_id}",
        )
        ids.append(case_id)
        delegation_modes[case_id] = mode
        splits[split] += 1
    _require(len(set(ids)) == len(ids), "confirmation manifest contains duplicate case ids")
    _require(MONOREPO_CASE in ids, f"confirmation manifest must contain {MONOREPO_CASE}")
    _require(
        splits == Counter({"development": 4, "held-out": 6}),
        "v8 confirmation manifest must contain 4 development and 6 held-out cases",
    )
    return ids, delegation_modes, _sha256(resolved)


def _load_legacy_manifest(
    path: Path,
    *,
    expected_case_id: str,
    label: str,
) -> tuple[str, dict[str, str], str]:
    resolved = path.expanduser().resolve()
    _require(resolved.is_file(), f"{label} manifest not found: {resolved}")
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise VerificationError(f"cannot read {label} manifest: {error}") from error
    _require(isinstance(payload, dict), f"{label} manifest must be an object")
    _require(payload.get("schema_version") == 2, f"{label} manifest must use schema 2")
    cases = payload.get("cases")
    _require(isinstance(cases, list), f"{label} manifest cases must be a list")
    _require(len(cases) == 1, f"{label} manifest must contain exactly one case")
    case = cases[0]
    _require(isinstance(case, dict), f"{label} manifest case must be an object")
    _require(
        case.get("id") == expected_case_id,
        f"{label} manifest case must be {expected_case_id}",
    )
    delegation = case.get("delegation")
    _require(isinstance(delegation, dict), f"{label} manifest must define delegation")
    _require(
        delegation.get("mode") == "required_when_available",
        f"{expected_case_id} must require Spark when available",
    )
    return (
        expected_case_id,
        {expected_case_id: "required_when_available"},
        _sha256(resolved),
    )


def load_legacy_manifest(path: Path) -> tuple[str, dict[str, str], str]:
    return _load_legacy_manifest(
        path,
        expected_case_id=LEGACY_CALCULATOR_CASE,
        label="legacy calculator",
    )


def load_relay_manifest(path: Path) -> tuple[str, dict[str, str], str]:
    return _load_legacy_manifest(
        path,
        expected_case_id=LEGACY_RELAY_CASE,
        label="legacy Relay Bench",
    )


def expected_release_cells(
    case_ids: Iterable[str],
    legacy_case_id: str = LEGACY_CALCULATOR_CASE,
    relay_case_id: str = LEGACY_RELAY_CASE,
) -> set[tuple[str, str, str, str]]:
    ids = tuple(case_ids)
    _require(MONOREPO_CASE in ids, f"agentic manifest must contain {MONOREPO_CASE}")
    _require(legacy_case_id not in ids, "legacy calculator must use a separate manifest")
    _require(relay_case_id not in ids, "legacy Relay Bench must use a separate manifest")
    _require(legacy_case_id != relay_case_id, "legacy manifests must use distinct case ids")
    non_anchor_ids = tuple(case_id for case_id in ids if case_id != MONOREPO_CASE)
    _require(len(non_anchor_ids) == 9, "agentic manifest must contain nine non-anchor cases")
    cells = {
        (case_id, V8_NO_SPARK_ARM, PRIMARY_SETTING[0], PRIMARY_SETTING[1])
        for case_id in ids
    }
    for model, effort in SETTINGS:
        for case_id in (legacy_case_id, relay_case_id):
            for arm in (*CONTROL_ARMS, V8_NO_SPARK_ARM, V8_SPARK_FORCED_ARM):
                cells.add((case_id, arm, model, effort))
        for arm in CONTROL_ARMS:
            cells.add((MONOREPO_CASE, arm, model, effort))
        cells.add((MONOREPO_CASE, V8_NO_SPARK_ARM, model, effort))
        cells.add((MONOREPO_CASE, V8_SPARK_FORCED_ARM, model, effort))
    cells.update(
        (case_id, V8_SPARK_AUTO_ARM, PRIMARY_SETTING[0], PRIMARY_SETTING[1])
        for case_id in non_anchor_ids
    )
    arm_counts = Counter(cell[1] for cell in cells)
    _require(arm_counts[V8_NO_SPARK_ARM] == 21, "release plan must contain 21 no-Spark cells")
    _require(
        sum(arm_counts[arm] for arm in CONTROL_ARMS) == 24,
        "release plan must contain 24 control cells",
    )
    _require(
        arm_counts[V8_SPARK_FORCED_ARM] == 12,
        "release plan must contain 12 forced-Spark cells",
    )
    _require(
        arm_counts[V8_SPARK_AUTO_ARM] == 9,
        "release plan must contain 9 auto-routing cells",
    )
    _require(len(cells) == 66, "internal release plan must contain exactly 66 cells")
    return cells


def frozen_hashes() -> dict[str, dict[str, str | None]]:
    for path in (V6_PROFILE, V6_POLICY, V8_PROFILE, V8_POLICY):
        _require(path.is_file(), f"frozen release input not found: {path}")
    return {
        STANDARD_ARM: {"profile_sha256": None, "policy_sha256": None},
        V6_ARM: {
            "profile_sha256": _sha256(V6_PROFILE),
            "policy_sha256": _sha256(V6_POLICY),
        },
        V8_NO_SPARK_ARM: {
            "profile_sha256": _sha256(V8_PROFILE),
            "policy_sha256": _sha256(V8_POLICY),
        },
        V8_SPARK_FORCED_ARM: {
            "profile_sha256": _sha256(V8_PROFILE),
            "policy_sha256": _sha256(V8_POLICY),
        },
        V8_SPARK_AUTO_ARM: {
            "profile_sha256": _sha256(V8_PROFILE),
            "policy_sha256": _sha256(V8_POLICY),
        },
    }


def _validate_arm_metadata(
    artifact_label: str,
    arms: list[str],
    metadata: object,
    hashes: dict[str, dict[str, str | None]],
    *,
    allow_legacy_none_routing: bool = False,
) -> None:
    _require(isinstance(metadata, dict), f"{artifact_label}: arm_metadata must be an object")
    _require(set(metadata) == set(arms), f"{artifact_label}: arm_metadata does not match arms")
    expectations = {
        STANDARD_ARM: (False, False, False, "none"),
        V6_ARM: (False, False, True, "none"),
        V8_NO_SPARK_ARM: (False, False, False, "none"),
        V8_SPARK_FORCED_ARM: (True, False, False, "forced"),
        V8_SPARK_AUTO_ARM: (True, True, False, "auto"),
    }
    for arm in arms:
        row = metadata.get(arm)
        _require(isinstance(row, dict), f"{artifact_label}: invalid metadata for {arm}")
        _require("v7" not in arm, f"{artifact_label}: v7 arm is forbidden")
        expected_spark, expected_multi_agent, expected_skill_input, expected_routing = (
            expectations[arm]
        )
        _require(
            row.get("spark_enabled") is expected_spark,
            f"{artifact_label}: spark flag mismatch for {arm}",
        )
        _require(
            row.get("multi_agent") is expected_multi_agent,
            f"{artifact_label}: multi-agent flag mismatch for {arm}",
        )
        _require(
            row.get("skill_input") is expected_skill_input,
            f"{artifact_label}: skill-input flag mismatch for {arm}",
        )
        observed_routing = row.get("routing_mode")
        _require(
            observed_routing == expected_routing
            or (
                allow_legacy_none_routing
                and expected_routing == "none"
                and observed_routing is None
            ),
            f"{artifact_label}: routing-mode mismatch for {arm}",
        )
        for key, expected in hashes[arm].items():
            _require(
                row.get(key) == expected,
                f"{artifact_label}: frozen {key} mismatch for {arm}",
            )


def _validate_spark_agent_metadata(
    artifact_label: str, arms: list[str], metadata: object
) -> None:
    if not any(arm in V8_SPARK_ARMS for arm in arms):
        _require(metadata is None, f"{artifact_label}: non-Spark artifact must not bind an agent")
        return
    _require(SPARK_AGENT.is_file(), f"frozen Spark agent not found: {SPARK_AGENT}")
    _require(isinstance(metadata, dict), f"{artifact_label}: spark_agent must be an object")
    _require(
        metadata.get("model") == SPARK_MODEL,
        f"{artifact_label}: Spark agent model mismatch",
    )
    _require(
        metadata.get("sha256") == _sha256(SPARK_AGENT),
        f"{artifact_label}: frozen Spark agent hash mismatch",
    )


def _usage_total(value: object, label: str) -> int:
    _require(isinstance(value, dict), f"{label} must be an object")
    total = value.get("totalTokens")
    _require(_is_int(total) and total >= 0, f"{label}.totalTokens must be a non-negative integer")
    return total


def _validate_task_correct_result(
    row: object,
    artifact_label: str,
    delegation_modes: dict[str, str],
) -> dict[str, Any]:
    _require(isinstance(row, dict), f"{artifact_label}: result must be an object")
    result = row
    case_id = result.get("case_id")
    arm = result.get("arm")
    label = f"{artifact_label}:{case_id}:{arm}"
    _require(isinstance(case_id, str) and bool(case_id), f"{label}: invalid case id")
    _require(case_id in delegation_modes, f"{label}: case is absent from confirmation manifest")
    _require(arm in KNOWN_ARMS, f"{label}: unknown or v7 arm")
    _require(result.get("trial") == 1, f"{label}: release trial must be 1")
    for field in (
        "task_pass",
        "acceptance_observed",
        "no_active_children",
    ):
        _require(result.get(field) is True, f"{label}: {field} must be true")
    for field in (
        "success",
        "protocol_pass",
        "routing_ok",
        "parent_work_replaced_ok",
        "all_spawned_workers_useful",
        "rtk_ok",
        "scope_ok",
        "usage_complete",
    ):
        _require(type(result.get(field)) is bool, f"{label}: {field} must be boolean")
    _require(
        result["success"] is (result["task_pass"] and result["protocol_pass"]),
        f"{label}: success must reflect task and protocol status",
    )
    _require(result.get("turn_status") == "completed", f"{label}: turn did not complete")
    grade = result.get("grade")
    _require(isinstance(grade, dict), f"{label}: grade must be an object")
    _require(grade.get("ok") is True, f"{label}: grade did not pass")
    _require(grade.get("score_pct") == 100.0, f"{label}: grade must be 100 percent")
    active = result.get("active_child_ids")
    _require(active == [], f"{label}: active children remain")

    parent_tokens = result.get("parent_total_tokens")
    child_tokens = result.get("child_total_tokens")
    combined_tokens = result.get("combined_total_tokens")
    _require(
        _is_int(parent_tokens) and parent_tokens > 0,
        f"{label}: parent token usage must be a positive integer",
    )
    _require(
        _is_int(child_tokens) and child_tokens >= 0,
        f"{label}: child token usage must be a non-negative integer",
    )
    _require(
        _is_int(combined_tokens) and combined_tokens == parent_tokens + child_tokens,
        f"{label}: combined token usage is inconsistent",
    )
    _require(
        _usage_total(result.get("parent_usage"), f"{label}:parent_usage") == parent_tokens,
        f"{label}: parent usage does not match parent_total_tokens",
    )
    child_usage = result.get("child_usage")
    _require(isinstance(child_usage, dict), f"{label}: child_usage must be an object")
    known_child_tokens = 0
    missing_child_usage: list[str] = []
    for child_id, value in child_usage.items():
        if value is None:
            missing_child_usage.append(child_id)
        else:
            known_child_tokens += _usage_total(value, f"{label}:child_usage:{child_id}")
    if result["usage_complete"]:
        _require(not missing_child_usage, f"{label}: complete usage has a missing child record")
        _require(
            known_child_tokens == child_tokens,
            f"{label}: child usage does not match child_total_tokens",
        )
    else:
        _require(
            known_child_tokens <= child_tokens,
            f"{label}: known child usage exceeds child_total_tokens",
        )

    spawned = result.get("actual_spawned_workers")
    useful = result.get("useful_worker_count")
    child_ids = result.get("child_thread_ids")
    useful_ids = result.get("useful_worker_ids")
    child_roles = result.get("child_roles")
    spawn_records = result.get("spawn_records")
    _require(_is_int(spawned) and spawned >= 0, f"{label}: invalid spawned-worker count")
    _require(_is_int(useful) and useful >= 0, f"{label}: invalid useful-worker count")
    _require(isinstance(child_ids, list), f"{label}: child_thread_ids must be a list")
    _require(isinstance(useful_ids, list), f"{label}: useful_worker_ids must be a list")
    _require(isinstance(child_roles, dict), f"{label}: child_roles must be an object")
    _require(isinstance(spawn_records, dict), f"{label}: spawn_records must be an object")
    _require(len(child_ids) == len(set(child_ids)), f"{label}: duplicate child thread ids")
    _require(len(child_ids) == spawned, f"{label}: spawned-worker count mismatch")
    _require(len(useful_ids) == useful, f"{label}: useful-worker count mismatch")
    _require(useful <= spawned, f"{label}: useful-worker count exceeds spawned workers")
    _require(set(useful_ids) <= set(child_ids), f"{label}: useful-worker ids mismatch")
    _require(
        result["all_spawned_workers_useful"] is (spawned == useful),
        f"{label}: all_spawned_workers_useful is inconsistent",
    )
    _require(set(child_usage) == set(child_ids), f"{label}: child usage/thread mismatch")
    _require(set(child_roles) == set(child_ids), f"{label}: child role/thread mismatch")
    _require(set(spawn_records) == set(child_ids), f"{label}: spawn record/thread mismatch")

    delegation_mode = delegation_modes[case_id]
    if arm not in V8_SPARK_ARMS:
        _require(spawned == 0, f"{label}: no-Spark/control arm spawned a worker")
        _require(child_tokens == 0, f"{label}: no-Spark/control arm used child tokens")
    elif delegation_mode == "forbidden":
        _require(spawned == 0, f"{label}: forbidden-routing case spawned a worker")
        _require(child_tokens == 0, f"{label}: forbidden-routing case used child tokens")
    else:
        _require(spawned >= 1, f"{label}: required-routing case spawned no workers")
        expected_origin = (
            "harness_thread" if arm == V8_SPARK_FORCED_ARM else "parent_agent"
        )
        for child_id in child_ids:
            _require(
                child_roles.get(child_id) == SPARK_ROLE,
                f"{label}: child {child_id} did not use exact role {SPARK_ROLE}",
            )
            record = spawn_records.get(child_id)
            _require(isinstance(record, dict), f"{label}: invalid spawn record for {child_id}")
            _require(
                record.get("model") == SPARK_MODEL,
                f"{label}: child {child_id} did not use exact model {SPARK_MODEL}",
            )
            _require(
                record.get("origin") == expected_origin,
                f"{label}: child {child_id} has invalid spawn origin",
            )
    wall = result.get("execution_duration_seconds")
    _require(
        isinstance(wall, (int, float)) and not isinstance(wall, bool) and wall > 0,
        f"{label}: execution duration must be positive",
    )
    first_spawn = result.get("first_spawn_seconds")
    if spawned:
        _require(
            isinstance(first_spawn, (int, float))
            and not isinstance(first_spawn, bool)
            and 0 <= first_spawn <= wall,
            f"{label}: invalid first-spawn timing",
        )
    else:
        _require(first_spawn is None, f"{label}: zero-worker arm has a spawn time")
    return result


def _is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _selection_cell(value: object, label: str, *, excluded: bool) -> tuple[str, str, str | None]:
    _require(isinstance(value, dict), f"{label} must be an object")
    expected_keys = {"case_id", "arm", "reason"} if excluded else {"case_id", "arm"}
    _require(set(value) == expected_keys, f"{label} has unexpected fields")
    case_id = value.get("case_id")
    arm = value.get("arm")
    _require(isinstance(case_id, str) and bool(case_id), f"{label} has invalid case_id")
    _require(isinstance(arm, str) and bool(arm), f"{label} has invalid arm")
    reason = value.get("reason") if excluded else None
    if excluded:
        _require(isinstance(reason, str) and bool(reason.strip()), f"{label} has no reason")
    return case_id, arm, reason


def load_retained_selection(path: Path) -> dict[str, Any]:
    resolved = path.expanduser().resolve()
    _require(resolved.is_file(), f"retained selection not found: {resolved}")
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise VerificationError(f"cannot read retained selection {resolved}: {error}") from error
    _require(isinstance(payload, dict), f"{resolved}: retained selection must be an object")
    _require(payload.get("schema_version") == 1, f"{resolved}: retained selection must use schema 1")
    source_path = payload.get("source_path")
    _require(isinstance(source_path, str) and bool(source_path), f"{resolved}: invalid source_path")
    source = (resolved.parent / source_path).resolve()
    source_sha256 = payload.get("source_sha256")
    source_runner_sha256 = payload.get("source_runner_sha256")
    no_spark_config_sha256 = payload.get("no_spark_config_sha256")
    _require(_is_sha256(source_sha256), f"{resolved}: invalid source_sha256")
    _require(_is_sha256(source_runner_sha256), f"{resolved}: invalid source_runner_sha256")
    _require(_is_sha256(no_spark_config_sha256), f"{resolved}: invalid no_spark_config_sha256")
    selected_values = payload.get("selected_cells")
    excluded_values = payload.get("excluded_cells")
    _require(
        isinstance(selected_values, list) and bool(selected_values),
        f"{resolved}: selected_cells must be non-empty",
    )
    _require(
        isinstance(excluded_values, list) and bool(excluded_values),
        f"{resolved}: excluded_cells must be non-empty",
    )
    selected = {
        (case_id, arm)
        for index, value in enumerate(selected_values)
        for case_id, arm, _ in [_selection_cell(value, f"{resolved}:selected_cells[{index}]", excluded=False)]
    }
    excluded_entries = [
        _selection_cell(value, f"{resolved}:excluded_cells[{index}]", excluded=True)
        for index, value in enumerate(excluded_values)
    ]
    excluded = {(case_id, arm): reason for case_id, arm, reason in excluded_entries}
    _require(len(selected) == len(selected_values), f"{resolved}: duplicate selected cells")
    _require(len(excluded) == len(excluded_values), f"{resolved}: duplicate excluded cells")
    _require(not selected.intersection(excluded), f"{resolved}: selected and excluded cells overlap")
    _require(
        all(arm in KNOWN_ARMS for _, arm in selected),
        f"{resolved}: selected cells contain an unknown or legacy arm",
    )
    _require(
        all(arm in (*KNOWN_ARMS, LEGACY_SPARK_ARM) for _, arm in excluded),
        f"{resolved}: excluded cells contain an unknown or v7 arm",
    )
    return {
        "descriptor_path": resolved,
        "descriptor_sha256": _sha256(resolved),
        "source_path": source,
        "source_sha256": source_sha256,
        "source_runner_sha256": source_runner_sha256,
        "no_spark_config_sha256": no_spark_config_sha256,
        "selected": selected,
        "excluded": excluded,
    }


def _read_artifact(
    path: Path,
    manifest_bindings: dict[str, dict[str, Any]],
    hashes: dict[str, dict[str, str | None]],
    *,
    retained_selection: dict[str, Any] | None = None,
) -> tuple[list[tuple[tuple[str, str, str, str], dict[str, Any]]], dict[str, Any]]:
    resolved = path.expanduser().resolve()
    _require(resolved.is_file(), f"raw artifact not found: {resolved}")
    label = str(resolved)
    source_sha256 = _sha256(resolved)
    if retained_selection is not None:
        _require(
            retained_selection["source_path"] == resolved,
            f"{label}: retained selection source path mismatch",
        )
        _require(
            retained_selection["source_sha256"] == source_sha256,
            f"{label}: retained source hash mismatch",
        )
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise VerificationError(f"{label}: cannot read raw artifact: {error}") from error
    _require(isinstance(payload, dict), f"{label}: artifact must be an object")
    _require(payload.get("schema_version") == 3, f"{label}: artifact must use schema 3")
    _require(payload.get("complete") is True, f"{label}: artifact is incomplete")
    _require(payload.get("repetitions") == 1, f"{label}: release artifacts use one repetition")
    _require(payload.get("seed") == RELEASE_SEED, f"{label}: release seed mismatch")
    manifest_sha256 = payload.get("cases_sha256")
    _require(
        isinstance(manifest_sha256, str) and manifest_sha256 in manifest_bindings,
        f"{label}: release manifest hash mismatch",
    )
    manifest_binding = manifest_bindings[manifest_sha256]
    delegation_modes = manifest_binding["delegation_modes"]
    publication = payload.get("publication_status")
    _require(isinstance(publication, dict), f"{label}: publication_status must be an object")
    _require(publication.get("matrix_complete") is True, f"{label}: artifact matrix is incomplete")
    model = payload.get("model")
    effort = payload.get("effort")
    _require((model, effort) in SETTINGS, f"{label}: unsupported model/effort release setting")
    arms = payload.get("arms")
    _require(isinstance(arms, list) and bool(arms), f"{label}: arms must be a non-empty list")
    _require(len(arms) == len(set(arms)), f"{label}: duplicate arms")
    allowed_source_arms = (*KNOWN_ARMS, LEGACY_SPARK_ARM) if retained_selection else KNOWN_ARMS
    _require(all(arm in allowed_source_arms for arm in arms), f"{label}: unknown or v7 arm")
    metadata = payload.get("arm_metadata")
    _require(isinstance(metadata, dict), f"{label}: arm_metadata must be an object")
    _require(set(metadata) == set(arms), f"{label}: arm_metadata does not match arms")
    selected_arms = (
        sorted({arm for _, arm in retained_selection["selected"]})
        if retained_selection
        else arms
    )
    selected_metadata = {arm: metadata[arm] for arm in selected_arms}
    _validate_arm_metadata(
        label,
        selected_arms,
        selected_metadata,
        hashes,
        allow_legacy_none_routing=retained_selection is not None,
    )
    if retained_selection is None or any(arm in V8_SPARK_ARMS for arm in selected_arms):
        _validate_spark_agent_metadata(label, selected_arms, payload.get("spark_agent"))
    results = payload.get("results")
    _require(isinstance(results, list) and bool(results), f"{label}: results must be non-empty")
    raw_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for index, raw_result in enumerate(results):
        _require(isinstance(raw_result, dict), f"{label}: result {index} must be an object")
        case_id = raw_result.get("case_id")
        arm = raw_result.get("arm")
        _require(isinstance(case_id, str) and bool(case_id), f"{label}: result {index} has no case id")
        _require(isinstance(arm, str) and arm in arms, f"{label}: result {index} has invalid arm")
        key = (case_id, arm)
        _require(key not in raw_by_key, f"{label}: duplicate source result {key}")
        raw_by_key[key] = raw_result

    selected_keys = set(raw_by_key)
    excluded_reasons: dict[tuple[str, str], str | None] = {}
    if retained_selection is not None:
        selected_keys = retained_selection["selected"]
        excluded_reasons = retained_selection["excluded"]
        declared = selected_keys.union(excluded_reasons)
        _require(
            declared == set(raw_by_key),
            f"{label}: retained selection must classify every source result exactly once",
        )
    cells: list[tuple[tuple[str, str, str, str], dict[str, Any]]] = []
    for key in sorted(selected_keys):
        result = _validate_task_correct_result(raw_by_key[key], label, delegation_modes)
        result["_wall_time_contended"] = payload.get("wall_time_contended") is True
        result["_source_sha256"] = source_sha256
        result["_source_path"] = _display_path(resolved)
        result["_source_jobs"] = payload.get("jobs")
        result["_retained_selection"] = retained_selection is not None
        arm = result["arm"]
        cells.append(((result["case_id"], arm, model, effort), result))
    excluded_cells = [
        {
            "case_id": case_id,
            "arm": arm,
            "model": model,
            "effort": effort,
            "reason": excluded_reasons[(case_id, arm)],
            "success": raw_by_key[(case_id, arm)].get("success"),
            "task_pass": raw_by_key[(case_id, arm)].get("task_pass"),
            "protocol_pass": raw_by_key[(case_id, arm)].get("protocol_pass"),
        }
        for case_id, arm in sorted(excluded_reasons)
    ]
    metadata = {
        "path": _display_path(resolved),
        "sha256": source_sha256,
        "manifest_kind": manifest_binding["kind"],
        "manifest_path": manifest_binding["path"],
        "manifest_sha256": manifest_sha256,
        "cells": len(cells),
        "model": model,
        "effort": effort,
        "retained_selection": retained_selection is not None,
        "selected_cells": [
            {"case_id": cell[0], "arm": cell[1], "model": model, "effort": effort}
            for cell in sorted(selected_keys)
        ],
        "excluded_cells": excluded_cells,
    }
    if retained_selection is not None:
        metadata.update(
            {
                "selection_path": _display_path(retained_selection["descriptor_path"]),
                "selection_sha256": retained_selection["descriptor_sha256"],
                "source_runner_sha256": retained_selection["source_runner_sha256"],
                "no_spark_config_sha256": retained_selection["no_spark_config_sha256"],
                "source_publication_status": publication,
            }
        )
    return cells, metadata


def _sum(rows: Iterable[dict[str, Any]], key: str) -> int:
    return sum(int(row[key]) for row in rows)


def _parent_table(
    by_cell: dict[tuple[str, str, str, str], dict[str, Any]]
) -> list[dict[str, Any]]:
    table: list[dict[str, Any]] = []
    for case_id in (LEGACY_CALCULATOR_CASE, LEGACY_RELAY_CASE, MONOREPO_CASE):
        for model, effort in SETTINGS:
            standard = by_cell[(case_id, STANDARD_ARM, model, effort)]
            v6 = by_cell[(case_id, V6_ARM, model, effort)]
            v8 = by_cell[(case_id, V8_NO_SPARK_ARM, model, effort)]
            standard_tokens = standard["parent_total_tokens"]
            v6_tokens = v6["parent_total_tokens"]
            v8_tokens = v8["parent_total_tokens"]
            table.append(
                {
                    "model": model,
                    "effort": effort,
                    "scope": case_id,
                    "standard_parent_tokens": standard_tokens,
                    "v6_parent_tokens": v6_tokens,
                    "v6_saved_tokens": standard_tokens - v6_tokens,
                    "v6_saved_pct": _percentage(standard_tokens, v6_tokens),
                    "v8_arm": V8_NO_SPARK_ARM,
                    "v8_parent_tokens": v8_tokens,
                    "v8_saved_vs_standard_tokens": standard_tokens - v8_tokens,
                    "v8_saved_vs_standard_pct": _percentage(standard_tokens, v8_tokens),
                    "v8_saved_vs_v6_tokens": v6_tokens - v8_tokens,
                    "v8_saved_vs_v6_pct": _percentage(v6_tokens, v8_tokens),
                    "correctness": {"standard": True, "v6": True, "v8": True},
                }
            )
    return table


def _pair_metrics(
    no_spark: dict[str, Any], spark: dict[str, Any], *, model: str, effort: str, case_id: str
) -> dict[str, Any]:
    saved = no_spark["parent_total_tokens"] - spark["parent_total_tokens"]
    spawned = spark["actual_spawned_workers"]
    wall_saved = no_spark["execution_duration_seconds"] - spark["execution_duration_seconds"]
    contended = bool(
        no_spark.get("_wall_time_contended") or spark.get("_wall_time_contended")
    )
    same_source = no_spark.get("_source_sha256") == spark.get("_source_sha256")
    baseline_reused = bool(no_spark.get("_retained_selection") and not same_source)
    return {
        "model": model,
        "effort": effort,
        "case_id": case_id,
        "spark_arm": spark["arm"],
        "no_spark_parent_tokens": no_spark["parent_total_tokens"],
        "spark_parent_tokens": spark["parent_total_tokens"],
        "parent_tokens_saved": saved,
        "parent_token_reduction_pct": _percentage(
            no_spark["parent_total_tokens"], spark["parent_total_tokens"]
        ),
        "spark_child_tokens": (
            spark["child_total_tokens"] if spark["usage_complete"] else None
        ),
        "spark_child_tokens_observed": spark["child_total_tokens"],
        "spark_child_usage_complete": spark["usage_complete"],
        "spark_combined_tokens": (
            spark["combined_total_tokens"] if spark["usage_complete"] else None
        ),
        "spark_combined_tokens_observed": spark["combined_total_tokens"],
        "spawned_workers": spawned,
        "useful_workers": spark["useful_worker_count"],
        "parent_tokens_saved_per_spawned_worker": (
            round(saved / spawned, 3) if spawned else None
        ),
        "no_spark_wall_seconds": no_spark["execution_duration_seconds"],
        "spark_wall_seconds": spark["execution_duration_seconds"],
        "wall_seconds_saved": round(wall_saved, 3),
        "wall_time_reduction_pct": _percentage(
            no_spark["execution_duration_seconds"], spark["execution_duration_seconds"]
        ),
        "wall_seconds_saved_per_spawned_worker": (
            round(wall_saved / spawned, 3) if spawned else None
        ),
        "spark_first_spawn_seconds": spark["first_spawn_seconds"],
        "spark_spawn_delay_pct": spark.get("spawn_delay_pct"),
        "wall_time_contended": contended,
        "baseline_reused": baseline_reused,
        "same_source_artifact": same_source,
        "same_batch": same_source,
        "wall_time_reportable": bool(not contended and same_source),
        "wall_time_comparison": (
            "same-batch"
            if not contended and same_source
            else "exploratory-reused-baseline"
            if baseline_reused
            else "exploratory"
        ),
        "correctness": {"no_spark": True, "spark": True},
        "spark_protocol_pass": spark["protocol_pass"],
        "spark_routing_pass": spark["routing_ok"],
        "spark_parent_work_replaced": spark["parent_work_replaced_ok"],
    }


def _forced_efficacy_table(
    by_cell: dict[tuple[str, str, str, str], dict[str, Any]]
) -> list[dict[str, Any]]:
    return [
        _pair_metrics(
            by_cell[(case_id, V8_NO_SPARK_ARM, model, effort)],
            by_cell[(case_id, V8_SPARK_FORCED_ARM, model, effort)],
            model=model,
            effort=effort,
            case_id=case_id,
        )
        for case_id in (LEGACY_CALCULATOR_CASE, LEGACY_RELAY_CASE, MONOREPO_CASE)
        for model, effort in SETTINGS
    ]


def _auto_routing_tables(
    case_ids: list[str],
    delegation_modes: dict[str, str],
    by_cell: dict[tuple[str, str, str, str], dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    model, effort = PRIMARY_SETTING
    case_rows: list[dict[str, Any]] = []
    pairs: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for case_id in case_ids:
        if case_id == MONOREPO_CASE:
            continue
        no_spark = by_cell[(case_id, V8_NO_SPARK_ARM, model, effort)]
        auto = by_cell[(case_id, V8_SPARK_AUTO_ARM, model, effort)]
        pairs.append((no_spark, auto))
        row = _pair_metrics(no_spark, auto, model=model, effort=effort, case_id=case_id)
        required = delegation_modes[case_id] == "required_when_available"
        row.update(
            {
                "delegation_mode": delegation_modes[case_id],
                "spawn_expected": required,
                "routing_pass": auto["routing_ok"],
                "protocol_pass": auto["protocol_pass"],
                "parent_work_replaced": auto["parent_work_replaced_ok"],
                "exact_role_model_origin_ok": True,
                "no_active_children": auto["no_active_children"],
            }
        )
        case_rows.append(row)

    no_spark_rows = [pair[0] for pair in pairs]
    auto_rows = [pair[1] for pair in pairs]
    required_cases = sum(
        delegation_modes[row["case_id"]] == "required_when_available" for row in auto_rows
    )
    forbidden_cases = len(auto_rows) - required_cases
    no_spark_parent = _sum(no_spark_rows, "parent_total_tokens")
    auto_parent = _sum(auto_rows, "parent_total_tokens")
    spawned = _sum(auto_rows, "actual_spawned_workers")
    usage_complete = all(row["usage_complete"] for row in auto_rows)
    observed_child_tokens = _sum(auto_rows, "child_total_tokens")
    observed_combined_tokens = _sum(auto_rows, "combined_total_tokens")
    summary = {
        "model": model,
        "effort": effort,
        "scope": "auto-routing-nine-case-suite",
        "cases": len(auto_rows),
        "required_cases": required_cases,
        "forbidden_cases": forbidden_cases,
        "routing_passes": sum(bool(row["routing_ok"]) for row in auto_rows),
        "routing_reliability_pct": round(
            sum(bool(row["routing_ok"]) for row in auto_rows) / len(auto_rows) * 100,
            3,
        ),
        "protocol_passes": sum(bool(row["protocol_pass"]) for row in auto_rows),
        "protocol_compliance_pct": round(
            sum(bool(row["protocol_pass"]) for row in auto_rows) / len(auto_rows) * 100,
            3,
        ),
        "required_cases_with_spawn": sum(
            delegation_modes[row["case_id"]] == "required_when_available"
            and row["actual_spawned_workers"] >= 1
            for row in auto_rows
        ),
        "forbidden_cases_quiescent": sum(
            delegation_modes[row["case_id"]] == "forbidden"
            and row["actual_spawned_workers"] == 0
            for row in auto_rows
        ),
        "no_spark_parent_tokens": no_spark_parent,
        "auto_parent_tokens": auto_parent,
        "parent_tokens_saved": no_spark_parent - auto_parent,
        "parent_token_reduction_pct": _percentage(no_spark_parent, auto_parent),
        "auto_child_tokens": observed_child_tokens if usage_complete else None,
        "auto_child_tokens_observed": observed_child_tokens,
        "auto_child_usage_complete": usage_complete,
        "auto_child_usage_complete_cells": sum(
            bool(row["usage_complete"]) for row in auto_rows
        ),
        "auto_combined_tokens": observed_combined_tokens if usage_complete else None,
        "auto_combined_tokens_observed": observed_combined_tokens,
        "spawned_workers": spawned,
        "useful_workers": _sum(auto_rows, "useful_worker_count"),
        "parent_tokens_saved_per_spawned_worker": (
            round((no_spark_parent - auto_parent) / spawned, 3) if spawned else None
        ),
        "all_children_drained": all(row["no_active_children"] for row in auto_rows),
        "all_spawned_workers_useful": all(
            row["all_spawned_workers_useful"] for row in auto_rows
        ),
    }
    return summary, case_rows


def verify_release(
    manifest: Path,
    legacy_manifest: Path,
    relay_manifest: Path,
    raw_artifacts: list[Path],
    retained_selections: list[Path] | None = None,
) -> dict[str, Any]:
    selection_paths = retained_selections or []
    _require(
        not selection_paths,
        "corrected additive release requires fresh raw artifacts; retained selections are forbidden",
    )
    _require(
        bool(raw_artifacts or selection_paths),
        "at least one raw artifact or retained selection is required",
    )
    case_ids, delegation_modes, manifest_sha256 = load_release_manifest(manifest)
    legacy_case_id, legacy_delegation_modes, legacy_manifest_sha256 = (
        load_legacy_manifest(legacy_manifest)
    )
    relay_case_id, relay_delegation_modes, relay_manifest_sha256 = (
        load_relay_manifest(relay_manifest)
    )
    _require(
        len({manifest_sha256, legacy_manifest_sha256, relay_manifest_sha256}) == 3,
        "agentic and legacy manifests must have distinct hashes",
    )
    expected = expected_release_cells(case_ids, legacy_case_id, relay_case_id)
    manifest_bindings = {
        manifest_sha256: {
            "kind": "agentic-suite",
            "path": _display_path(manifest),
            "delegation_modes": delegation_modes,
        },
        legacy_manifest_sha256: {
            "kind": "legacy-calculator-anchor",
            "path": _display_path(legacy_manifest),
            "delegation_modes": legacy_delegation_modes,
        },
        relay_manifest_sha256: {
            "kind": "legacy-relay-bench-anchor",
            "path": _display_path(relay_manifest),
            "delegation_modes": relay_delegation_modes,
        },
    }
    hashes = frozen_hashes()
    observed: list[tuple[tuple[str, str, str, str], dict[str, Any]]] = []
    sources: list[dict[str, Any]] = []
    ordinary_sources = {path.expanduser().resolve() for path in raw_artifacts}
    loaded_selections = [load_retained_selection(path) for path in selection_paths]
    for selection in loaded_selections:
        _require(
            selection["source_path"] not in ordinary_sources,
            f"retained source also supplied as ordinary raw artifact: {selection['source_path']}",
        )
    for raw in sorted(raw_artifacts, key=lambda value: str(value.expanduser().resolve())):
        cells, source = _read_artifact(
            raw,
            manifest_bindings,
            hashes,
        )
        observed.extend(cells)
        sources.append(source)
    for selection in sorted(loaded_selections, key=lambda value: str(value["descriptor_path"])):
        cells, source = _read_artifact(
            selection["source_path"],
            manifest_bindings,
            hashes,
            retained_selection=selection,
        )
        observed.extend(cells)
        sources.append(source)
    keys = [cell for cell, _ in observed]
    duplicates = sorted(cell for cell, count in Counter(keys).items() if count > 1)
    _require(not duplicates, f"duplicate release cells: {duplicates}")
    actual = set(keys)
    missing = sorted(expected - actual)
    unexpected = sorted(actual - expected)
    _require(not missing, f"missing release cells: {missing}")
    _require(not unexpected, f"unexpected release cells: {unexpected}")
    _require(len(observed) == 66, "release matrix must contain exactly 66 results")
    by_cell = dict(observed)
    candidate_rows = [row for cell, row in observed if cell[1] in V8_ARMS]
    control_rows = [row for cell, row in observed if cell[1] in CONTROL_ARMS]
    _require(len(candidate_rows) == 42, "release matrix must contain 42 v8 candidate cells")
    _require(len(control_rows) == 24, "release matrix must contain 24 control cells")
    arm_counts = Counter(cell[1] for cell, _ in observed)
    _require(arm_counts[V8_NO_SPARK_ARM] == 21, "release matrix must contain 21 no-Spark cells")
    _require(
        arm_counts[V8_SPARK_FORCED_ARM] == 12,
        "release matrix must contain 12 forced-Spark cells",
    )
    _require(
        arm_counts[V8_SPARK_AUTO_ARM] == 9,
        "release matrix must contain 9 auto-routing cells",
    )
    _require(
        all(row["no_active_children"] for row in candidate_rows),
        "all v8 candidate cells must drain children",
    )
    forced_efficacy = _forced_efficacy_table(by_cell)
    auto_summary, auto_case_rows = _auto_routing_tables(
        case_ids, delegation_modes, by_cell
    )
    protocol_passes = sum(bool(row["protocol_pass"]) for _, row in observed)
    candidate_protocol_passes = sum(bool(row["protocol_pass"]) for row in candidate_rows)
    rtk_passes = sum(bool(row["rtk_ok"]) for _, row in observed)
    scope_passes = sum(bool(row["scope_ok"]) for _, row in observed)
    usage_complete_cells = sum(bool(row["usage_complete"]) for _, row in observed)
    usage_incomplete_cells = [
        {
            "case_id": case_id,
            "arm": arm,
            "model": model,
            "effort": effort,
        }
        for (case_id, arm, model, effort), row in observed
        if not row["usage_complete"]
    ]
    comparative_coverage = {
        "status": "three-task-comparison-complete; suite-wide-controls-not-run",
        "fresh_raw_sources": True,
        "case_universe": len(case_ids) + 2,
        "comparative_case_ids": [legacy_case_id, relay_case_id, MONOREPO_CASE],
        "comparative_cases": [
            {
                "case_id": case_id,
                "manifest_kind": (
                    "legacy-calculator-anchor"
                    if case_id == legacy_case_id
                    else "legacy-relay-bench-anchor"
                    if case_id == relay_case_id
                    else "agentic-suite"
                ),
                "cells": 16,
                "arms": [
                    STANDARD_ARM,
                    V6_ARM,
                    V8_NO_SPARK_ARM,
                    V8_SPARK_FORCED_ARM,
                ],
                "settings": [
                    {"model": model, "effort": effort} for model, effort in SETTINGS
                ],
                "standard_v6_v8_complete": True,
                "forced_spark_complete": True,
            }
            for case_id in (legacy_case_id, relay_case_id, MONOREPO_CASE)
        ],
        "standard_v6_v8_scope": (
            "legacy-calculator-legacy-relay-bench-and-monorepo-migration-only"
        ),
        "suite_wide_standard_v6_v8": False,
        "agentic_manifest_cases": len(case_ids),
        "agentic_selected_cases": len(case_ids),
        "agentic_selected_cells": 34,
        "agentic_non_anchor_cases": len(case_ids) - 1,
        "agentic_non_anchor_cells": 18,
        "agentic_non_anchor_arms": [V8_NO_SPARK_ARM, V8_SPARK_AUTO_ARM],
        "agentic_non_anchor_standard_cells": 0,
        "agentic_non_anchor_v6_cells": 0,
        "legacy_anchor_cells": 16,
        "relay_anchor_cells": 16,
        "migration_anchor_cells": 16,
    }
    return {
        "schema_version": 3,
        "verified": True,
        "acceptance_policy": {
            "hard_gate": "task_correctness",
            "treatment_integrity_hard_gate": True,
            "task_correct_cells": len(observed),
            "task_correctness_pct": 100.0,
            "protocol_pass_cells": protocol_passes,
            "protocol_compliance_pct": round(protocol_passes / len(observed) * 100, 3),
            "candidate_protocol_pass_cells": candidate_protocol_passes,
            "candidate_protocol_compliance_pct": round(
                candidate_protocol_passes / len(candidate_rows) * 100,
                3,
            ),
            "rtk_pass_cells": rtk_passes,
            "rtk_compliance_pct": round(rtk_passes / len(observed) * 100, 3),
            "scope_pass_cells": scope_passes,
            "scope_compliance_pct": round(scope_passes / len(observed) * 100, 3),
            "usage_complete_cells": usage_complete_cells,
            "usage_completeness_pct": round(
                usage_complete_cells / len(observed) * 100, 3
            ),
            "usage_incomplete_cells": usage_incomplete_cells,
            "protocol_is_disclosed_not_release_blocking": True,
            "scope_is_disclosed_not_release_blocking": True,
            "incomplete_child_usage_is_disclosed_not_release_blocking": True,
        },
        "release_plan": {
            "seed": RELEASE_SEED,
            "total_cells": len(observed),
            "tuning_cells_outside_release_verifier": 6,
            "scored_cells_including_tuning": len(observed) + 6,
            "candidate_cells": len(candidate_rows),
            "control_cells": len(control_rows),
            "arm_cells": dict(sorted(arm_counts.items())),
            "full_suite_cases": len(case_ids) + 2,
            "agentic_manifest_cases": len(case_ids),
            "confirmation_manifest": _display_path(manifest),
            "confirmation_sha256": manifest_sha256,
            "legacy_manifest": _display_path(legacy_manifest),
            "legacy_manifest_sha256": legacy_manifest_sha256,
            "relay_manifest": _display_path(relay_manifest),
            "relay_manifest_sha256": relay_manifest_sha256,
            "case_universe": len(case_ids) + 2,
            "legacy_anchor_cells": 16,
            "relay_anchor_cells": 16,
            "migration_anchor_cells": 16,
            "agentic_non_anchor_cells": 18,
        },
        "comparative_coverage": comparative_coverage,
        "frozen_hashes": hashes,
        "source_artifacts": sources,
        "parent_token_table": _parent_table(by_cell),
        "forced_efficacy_table": forced_efficacy,
        "auto_routing_summary": auto_summary,
        "auto_routing_case_rows": auto_case_rows,
    }


def write_summary(path: Path, payload: dict[str, Any]) -> None:
    resolved = path.expanduser().resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{resolved.name}.", suffix=".tmp", dir=resolved.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(rendered)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(resolved)
    finally:
        if temporary.exists():
            temporary.unlink()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--legacy-manifest", type=Path, default=DEFAULT_LEGACY_MANIFEST)
    parser.add_argument("--relay-manifest", type=Path, default=DEFAULT_RELAY_MANIFEST)
    parser.add_argument("--raw", type=Path, action="append", default=[])
    parser.add_argument("--retained-selection", type=Path, action="append", default=[])
    parser.add_argument("--output", type=Path, default=None)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        summary = verify_release(
            args.manifest,
            args.legacy_manifest,
            args.relay_manifest,
            args.raw,
            args.retained_selection,
        )
    except (OSError, VerificationError, json.JSONDecodeError) as error:
        print(f"verify-v8-release: {error}", file=os.sys.stderr)
        return 2
    if args.output is not None:
        write_summary(args.output, summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
