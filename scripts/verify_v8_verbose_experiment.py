#!/usr/bin/env python3
"""Verify the 42-cell verbose-v8 experiment against the accepted v8 release."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

try:
    from scripts.verify_v8_release import (
        LEGACY_CALCULATOR_CASE,
        LEGACY_RELAY_CASE,
        MONOREPO_CASE,
        PRIMARY_SETTING,
        RELEASE_SEED,
        SETTINGS,
        SPARK_AGENT,
        SPARK_MODEL,
        SPARK_ROLE,
        V8_ARMS,
        V8_NO_SPARK_ARM,
        V8_SPARK_ARMS,
        V8_SPARK_AUTO_ARM,
        V8_SPARK_FORCED_ARM,
        VerificationError,
        expected_release_cells,
        load_legacy_manifest,
        load_relay_manifest,
        load_release_manifest,
        write_summary,
    )
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from verify_v8_release import (  # type: ignore[no-redef]
        LEGACY_CALCULATOR_CASE,
        LEGACY_RELAY_CASE,
        MONOREPO_CASE,
        PRIMARY_SETTING,
        RELEASE_SEED,
        SETTINGS,
        SPARK_AGENT,
        SPARK_MODEL,
        SPARK_ROLE,
        V8_ARMS,
        V8_NO_SPARK_ARM,
        V8_SPARK_ARMS,
        V8_SPARK_AUTO_ARM,
        V8_SPARK_FORCED_ARM,
        VerificationError,
        expected_release_cells,
        load_legacy_manifest,
        load_relay_manifest,
        load_release_manifest,
        write_summary,
    )


ROOT = Path(__file__).parents[1]
DEFAULT_MANIFEST = ROOT / "benchmarks" / "agentic-v8-confirmation.json"
DEFAULT_LEGACY_MANIFEST = ROOT / "benchmarks" / "agentic-v8-legacy-calculator.json"
DEFAULT_RELAY_MANIFEST = ROOT / "benchmarks" / "agentic-v8-legacy-relay-bench.json"
DEFAULT_VERBOSE_PROFILE = (
    ROOT / "benchmarks" / "experiments" / "v8-verbose" / "profile.config.toml"
)
DEFAULT_VERBOSE_POLICY = (
    ROOT / "benchmarks" / "experiments" / "v8-verbose" / "SKILL.md"
)
DEFAULT_RELEASE_SUMMARY = ROOT / "benchmarks" / "results" / "v8-release-summary.json"
DEFAULT_OUTPUT = ROOT / "benchmarks" / "results" / "v8-verbose-comparison.json"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _display(path: Path) -> str:
    resolved = path.expanduser().resolve()
    try:
        return str(resolved.relative_to(ROOT))
    except ValueError:
        return str(resolved)


def _load_json(path: Path, label: str) -> dict[str, Any]:
    resolved = path.expanduser().resolve()
    _require(resolved.is_file(), f"{label} not found: {resolved}")
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise VerificationError(f"cannot read {label}: {error}") from error
    _require(isinstance(payload, dict), f"{label} must be an object")
    return payload


def expected_verbose_cells(
    case_ids: list[str],
    legacy_case_id: str = LEGACY_CALCULATOR_CASE,
    relay_case_id: str = LEGACY_RELAY_CASE,
) -> set[tuple[str, str, str, str]]:
    return {
        cell
        for cell in expected_release_cells(case_ids, legacy_case_id, relay_case_id)
        if cell[1] in V8_ARMS
    }


def _manifest_context(
    manifest: Path, legacy_manifest: Path, relay_manifest: Path
) -> tuple[list[str], dict[str, str], dict[str, dict[str, Any]]]:
    case_ids, delegation, manifest_sha = load_release_manifest(manifest)
    legacy_id, legacy_delegation, legacy_sha = load_legacy_manifest(legacy_manifest)
    relay_id, relay_delegation, relay_sha = load_relay_manifest(relay_manifest)
    modes = {**delegation, **legacy_delegation, **relay_delegation}
    bindings = {
        manifest_sha: {"kind": "agentic-suite", "delegation": delegation},
        legacy_sha: {"kind": "legacy-calculator-anchor", "delegation": legacy_delegation},
        relay_sha: {"kind": "legacy-relay-bench-anchor", "delegation": relay_delegation},
    }
    _require(len(bindings) == 3, "manifest hashes must be distinct")
    _require(legacy_id == LEGACY_CALCULATOR_CASE, "calculator manifest mismatch")
    _require(relay_id == LEGACY_RELAY_CASE, "Relay manifest mismatch")
    return case_ids, modes, bindings


def _resolve_source(summary_path: Path, value: str) -> Path:
    candidate = Path(value).expanduser()
    if candidate.is_absolute():
        return candidate.resolve()
    root_candidate = (ROOT / candidate).resolve()
    if root_candidate.is_file():
        return root_candidate
    return (summary_path.expanduser().resolve().parent / candidate).resolve()


def _accepted_mechy_reference(
    release_summary: Path,
    expected: set[tuple[str, str, str, str]],
) -> tuple[dict[tuple[str, str, str, str], dict[str, Any]], dict[str, str], list[dict[str, Any]]]:
    summary = _load_json(release_summary, "accepted release summary")
    _require(summary.get("schema_version") == 3, "release summary must use schema 3")
    _require(summary.get("verified") is True, "release summary is not verified")
    plan = summary.get("release_plan")
    _require(isinstance(plan, dict), "release summary has no release plan")
    _require(plan.get("seed") == RELEASE_SEED, "release summary seed mismatch")
    _require(plan.get("candidate_cells") == 42, "release summary must contain 42 v8 cells")
    sources = summary.get("source_artifacts")
    _require(isinstance(sources, list) and len(sources) == 13, "release summary must bind 13 sources")
    rows: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    runtime: dict[str, str] = {}
    provenance: list[dict[str, Any]] = []
    for index, source in enumerate(sources):
        _require(isinstance(source, dict), f"release source {index} must be an object")
        source_path = source.get("path")
        _require(isinstance(source_path, str) and source_path, f"release source {index} has no path")
        path = _resolve_source(release_summary, source_path)
        expected_sha = source.get("sha256")
        _require(expected_sha == _sha256(path), f"release source hash mismatch: {source_path}")
        artifact = _load_json(path, f"release source {source_path}")
        model, effort = artifact.get("model"), artifact.get("effort")
        _require((model, effort) in SETTINGS, f"release source has unsupported runtime: {source_path}")
        for field in ("codex_version", "rtk_version"):
            value = artifact.get(field)
            _require(isinstance(value, str) and value, f"release source lacks {field}: {source_path}")
            previous = runtime.setdefault(field, value)
            _require(previous == value, f"release sources disagree on {field}")
        results = artifact.get("results")
        _require(isinstance(results, list), f"release source has no results: {source_path}")
        for result in results:
            if not isinstance(result, dict) or result.get("arm") not in V8_ARMS:
                continue
            key = (result.get("case_id"), result.get("arm"), model, effort)
            _require(key in expected, f"unexpected mechy v8 cell: {key}")
            _require(key not in rows, f"duplicate mechy v8 cell: {key}")
            _require(result.get("task_pass") is True, f"accepted mechy cell is not task-correct: {key}")
            rows[key] = result
        provenance.append({"path": _display(path), "sha256": expected_sha})
    _require(set(rows) == expected, "release-summary provenance does not cover exact 42 mechy cells")
    return rows, runtime, provenance


def _validate_result(
    result: object,
    *,
    label: str,
    delegation_mode: str,
    task_correct: bool = True,
) -> dict[str, Any]:
    _require(isinstance(result, dict), f"{label}: result must be an object")
    row = result
    arm = row.get("arm")
    _require(arm in V8_ARMS, f"{label}: invalid v8 arm")
    _require(row.get("trial") == 1, f"{label}: trial must be 1")
    _require(
        row.get("task_pass") is task_correct,
        f"{label}: unexpected task-correctness status",
    )
    _require(row.get("acceptance_observed") is True, f"{label}: acceptance was not observed")
    _require(row.get("turn_status") == "completed", f"{label}: turn did not complete")
    _require(row.get("no_active_children") is True, f"{label}: active children remain")
    _require(row.get("active_child_ids") == [], f"{label}: active child ids remain")
    grade = row.get("grade")
    _require(isinstance(grade, dict), f"{label}: grade is missing")
    if task_correct:
        _require(grade.get("ok") is True, f"{label}: grade failed")
        _require(grade.get("score_pct") == 100.0, f"{label}: grade is not 100 percent")
    else:
        _require(grade.get("ok") is False, f"{label}: failed attempt has a passing grade")
    for field in ("protocol_pass", "scope_ok", "usage_complete", "rtk_ok"):
        _require(type(row.get(field)) is bool, f"{label}: {field} must be boolean")
    parent = row.get("parent_total_tokens")
    _require(type(parent) is int and parent > 0, f"{label}: invalid parent tokens")
    spawned = row.get("actual_spawned_workers")
    useful = row.get("useful_worker_count")
    child_ids = row.get("child_thread_ids")
    useful_ids = row.get("useful_worker_ids")
    roles = row.get("child_roles")
    records = row.get("spawn_records")
    usage = row.get("child_usage")
    _require(type(spawned) is int and spawned >= 0, f"{label}: invalid spawn count")
    _require(type(useful) is int and 0 <= useful <= spawned, f"{label}: invalid useful count")
    _require(isinstance(child_ids, list) and len(child_ids) == spawned, f"{label}: child ids mismatch")
    _require(len(child_ids) == len(set(child_ids)), f"{label}: duplicate child ids")
    _require(isinstance(useful_ids, list) and len(useful_ids) == useful, f"{label}: useful ids mismatch")
    _require(set(useful_ids) <= set(child_ids), f"{label}: unknown useful child")
    _require(isinstance(roles, dict) and set(roles) == set(child_ids), f"{label}: child roles mismatch")
    _require(isinstance(records, dict) and set(records) == set(child_ids), f"{label}: spawn records mismatch")
    _require(isinstance(usage, dict) and set(usage) == set(child_ids), f"{label}: child usage mismatch")
    should_spawn = arm in V8_SPARK_ARMS and delegation_mode != "forbidden"
    if should_spawn:
        _require(spawned >= 1, f"{label}: required Spark treatment did not spawn")
        origin = "harness_thread" if arm == V8_SPARK_FORCED_ARM else "parent_agent"
        for child_id in child_ids:
            record = records[child_id]
            _require(roles[child_id] == SPARK_ROLE, f"{label}: wrong child role")
            _require(isinstance(record, dict), f"{label}: invalid spawn record")
            _require(record.get("model") == SPARK_MODEL, f"{label}: wrong child model")
            _require(record.get("origin") == origin, f"{label}: wrong spawn origin")
    else:
        _require(spawned == 0, f"{label}: no-Spark/forbidden treatment spawned")
    child_tokens = row.get("child_total_tokens")
    combined = row.get("combined_total_tokens")
    if row["usage_complete"]:
        _require(type(child_tokens) is int and child_tokens >= 0, f"{label}: invalid child tokens")
        _require(combined == parent + child_tokens, f"{label}: combined tokens mismatch")
        _require(all(value is not None for value in usage.values()), f"{label}: complete usage is missing")
    else:
        _require(child_tokens is None or type(child_tokens) is int, f"{label}: invalid partial child tokens")
        _require(combined is None or type(combined) is int, f"{label}: invalid partial combined tokens")
    return row


def _aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    mechy_parent = sum(row["mechy_parent_tokens"] for row in rows)
    verbose_parent = sum(row["verbose_parent_tokens"] for row in rows)
    saved = mechy_parent - verbose_parent
    spawned = sum(row["verbose_spawned_workers"] for row in rows)
    usage_complete = all(row["verbose_usage_complete"] for row in rows)
    child_values = [row["verbose_child_tokens"] for row in rows]
    child_total = sum(child_values) if usage_complete and all(value is not None for value in child_values) else None
    return {
        "cells": len(rows),
        "mechy_parent_tokens": mechy_parent,
        "verbose_parent_tokens": verbose_parent,
        "parent_tokens_saved": saved,
        "parent_token_reduction_pct": round(saved / mechy_parent * 100, 3),
        "verbose_spawned_workers": spawned,
        "verbose_useful_workers": sum(row["verbose_useful_workers"] for row in rows),
        "parent_tokens_saved_per_spawned_worker": round(saved / spawned, 3) if spawned else None,
        "verbose_child_tokens": child_total,
        "verbose_combined_tokens": verbose_parent + child_total if child_total is not None else None,
        "protocol_pass_cells": sum(row["verbose_protocol_pass"] for row in rows),
        "scope_pass_cells": sum(row["verbose_scope_ok"] for row in rows),
        "complete_child_usage_cells": sum(row["verbose_usage_complete"] for row in rows),
    }


def _spark_efficacy(
    rows: list[dict[str, Any]], spark_arm: str
) -> dict[str, Any]:
    no_spark = {
        (row["case_id"], row["model"], row["effort"]): row
        for row in rows
        if row["arm"] == V8_NO_SPARK_ARM
    }
    spark_rows = [row for row in rows if row["arm"] == spark_arm]
    pairs: list[dict[str, Any]] = []
    for spark in spark_rows:
        key = (spark["case_id"], spark["model"], spark["effort"])
        _require(key in no_spark, f"missing verbose no-Spark pair for {key}")
        baseline = no_spark[key]
        saved = baseline["verbose_parent_tokens"] - spark["verbose_parent_tokens"]
        spawned = spark["verbose_spawned_workers"]
        pairs.append(
            {
                "case_id": key[0],
                "model": key[1],
                "effort": key[2],
                "no_spark_parent_tokens": baseline["verbose_parent_tokens"],
                "spark_parent_tokens": spark["verbose_parent_tokens"],
                "parent_tokens_saved": saved,
                "parent_token_reduction_pct": round(
                    saved / baseline["verbose_parent_tokens"] * 100, 3
                ),
                "spawned_workers": spawned,
                "useful_workers": spark["verbose_useful_workers"],
                "parent_tokens_saved_per_spawned_worker": (
                    round(saved / spawned, 3) if spawned else None
                ),
                "spark_child_tokens": spark["verbose_child_tokens"],
                "spark_combined_tokens": spark["verbose_combined_tokens"],
            }
        )
    no_parent = sum(row["no_spark_parent_tokens"] for row in pairs)
    spark_parent = sum(row["spark_parent_tokens"] for row in pairs)
    saved = no_parent - spark_parent
    spawned = sum(row["spawned_workers"] for row in pairs)
    child_values = [row["spark_child_tokens"] for row in pairs]
    child_total = (
        sum(child_values) if all(value is not None for value in child_values) else None
    )
    return {
        "spark_arm": spark_arm,
        "pairs": len(pairs),
        "no_spark_parent_tokens": no_parent,
        "spark_parent_tokens": spark_parent,
        "parent_tokens_saved": saved,
        "parent_token_reduction_pct": round(saved / no_parent * 100, 3),
        "spawned_workers": spawned,
        "useful_workers": sum(row["useful_workers"] for row in pairs),
        "parent_tokens_saved_per_spawned_worker": (
            round(saved / spawned, 3) if spawned else None
        ),
        "spark_child_tokens": child_total,
        "spark_combined_tokens": (
            spark_parent + child_total if child_total is not None else None
        ),
        "rows": pairs,
    }


def verify_verbose_experiment(
    *,
    manifest: Path,
    legacy_manifest: Path,
    relay_manifest: Path,
    verbose_profile: Path,
    verbose_policy: Path,
    verbose_raw_artifacts: list[Path],
    release_summary: Path,
) -> dict[str, Any]:
    _require(
        len(verbose_raw_artifacts) >= 13,
        "verbose experiment requires at least the 13 planned source artifacts",
    )
    _require(verbose_profile.is_file(), f"verbose profile not found: {verbose_profile}")
    _require(verbose_policy.is_file(), f"verbose policy not found: {verbose_policy}")
    case_ids, modes, bindings = _manifest_context(manifest, legacy_manifest, relay_manifest)
    expected = expected_verbose_cells(case_ids)
    _require(len(expected) == 42, "verbose experiment must contain exactly 42 cells")
    mechy, runtime, mechy_sources = _accepted_mechy_reference(release_summary, expected)
    profile_sha = _sha256(verbose_profile)
    policy_sha = _sha256(verbose_policy)
    spark_sha = _sha256(SPARK_AGENT)
    observed: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    verbose_sources: list[dict[str, Any]] = []
    excluded_failed_attempts: list[dict[str, Any]] = []
    skill_inputs: set[bool] = set()
    for raw in verbose_raw_artifacts:
        artifact = _load_json(raw, f"verbose artifact {raw}")
        label = str(raw.expanduser().resolve())
        _require(artifact.get("schema_version") == 3, f"{label}: schema must be 3")
        _require(type(artifact.get("complete")) is bool, f"{label}: complete must be boolean")
        _require(artifact.get("repetitions") == 1, f"{label}: repetitions must be 1")
        _require(artifact.get("seed") == RELEASE_SEED, f"{label}: seed mismatch")
        manifest_sha = artifact.get("cases_sha256")
        _require(manifest_sha in bindings, f"{label}: manifest hash mismatch")
        _require(artifact.get("codex_version") == runtime["codex_version"], f"{label}: Codex runtime mismatch")
        _require(artifact.get("rtk_version") == runtime["rtk_version"], f"{label}: RTK runtime mismatch")
        model, effort = artifact.get("model"), artifact.get("effort")
        _require((model, effort) in SETTINGS, f"{label}: unsupported parent runtime")
        arms = artifact.get("arms")
        _require(isinstance(arms, list) and arms and all(arm in V8_ARMS for arm in arms), f"{label}: verbose arms must be v8-only")
        metadata = artifact.get("arm_metadata")
        _require(isinstance(metadata, dict) and set(metadata) == set(arms), f"{label}: arm metadata mismatch")
        for arm in arms:
            arm_meta = metadata[arm]
            _require(isinstance(arm_meta, dict), f"{label}: invalid metadata for {arm}")
            _require(arm_meta.get("profile_sha256") == profile_sha, f"{label}: verbose profile hash mismatch")
            _require(arm_meta.get("policy_sha256") == policy_sha, f"{label}: verbose policy hash mismatch")
            _require(type(arm_meta.get("skill_input")) is bool, f"{label}: skill_input must be boolean")
            skill_inputs.add(arm_meta["skill_input"])
        spark = artifact.get("spark_agent")
        if any(arm in V8_SPARK_ARMS for arm in arms):
            _require(isinstance(spark, dict), f"{label}: Spark metadata is required")
            _require(spark.get("sha256") == spark_sha, f"{label}: Spark agent hash mismatch")
            _require(spark.get("model") == SPARK_MODEL, f"{label}: Spark model mismatch")
            _require(spark.get("effort") == "medium", f"{label}: Spark effort mismatch")
        else:
            _require(spark is None, f"{label}: no-Spark-only artifact has Spark metadata")
        results = artifact.get("results")
        _require(isinstance(results, list) and results, f"{label}: results are missing")
        for result in results:
            _require(isinstance(result, dict), f"{label}: invalid result")
            case_id, arm = result.get("case_id"), result.get("arm")
            key = (case_id, arm, model, effort)
            _require(key in expected, f"{label}: unexpected verbose cell {key}")
            result_label = f"{label}:{case_id}:{arm}"
            if result.get("task_pass") is True:
                _require(key not in observed, f"duplicate accepted verbose cell: {key}")
                observed[key] = _validate_result(
                    result,
                    label=result_label,
                    delegation_mode=modes[case_id],
                )
            else:
                _validate_result(
                    result,
                    label=result_label,
                    delegation_mode=modes[case_id],
                    task_correct=False,
                )
                excluded_failed_attempts.append(
                    {
                        "case_id": case_id,
                        "arm": arm,
                        "model": model,
                        "effort": effort,
                        "source": _display(raw),
                        "reason": "task-correctness-failure-replaced-by-single-targeted-retry",
                    }
                )
        verbose_sources.append(
            {
                "path": _display(raw),
                "sha256": _sha256(raw),
                "cells": len(results),
                "artifact_complete": artifact["complete"],
                "accepted_cells": sum(result.get("task_pass") is True for result in results),
                "failed_cells": sum(result.get("task_pass") is False for result in results),
            }
        )
    _require(set(observed) == expected, "verbose artifacts do not cover exact 42-cell matrix")
    _require(skill_inputs == {False}, "verbose treatment must keep skill_input=false")

    comparisons: list[dict[str, Any]] = []
    for key in sorted(expected):
        baseline = mechy[key]
        candidate = observed[key]
        saved = baseline["parent_total_tokens"] - candidate["parent_total_tokens"]
        spawned = candidate["actual_spawned_workers"]
        usage_complete = candidate["usage_complete"]
        child_tokens = candidate.get("child_total_tokens") if usage_complete else None
        comparisons.append(
            {
                "case_id": key[0],
                "arm": key[1],
                "model": key[2],
                "effort": key[3],
                "mechy_parent_tokens": baseline["parent_total_tokens"],
                "verbose_parent_tokens": candidate["parent_total_tokens"],
                "parent_tokens_saved": saved,
                "parent_token_reduction_pct": round(saved / baseline["parent_total_tokens"] * 100, 3),
                "mechy_spawned_workers": baseline["actual_spawned_workers"],
                "verbose_spawned_workers": spawned,
                "verbose_useful_workers": candidate["useful_worker_count"],
                "parent_tokens_saved_per_spawned_worker": round(saved / spawned, 3) if spawned else None,
                "verbose_child_tokens": child_tokens,
                "verbose_combined_tokens": candidate.get("combined_total_tokens") if usage_complete else None,
                "verbose_protocol_pass": candidate["protocol_pass"],
                "verbose_scope_ok": candidate["scope_ok"],
                "verbose_usage_complete": usage_complete,
            }
        )
    by_arm = {
        arm: _aggregate([row for row in comparisons if row["arm"] == arm])
        for arm in V8_ARMS
    }
    protocol_failures = [
        {key: row[key] for key in ("case_id", "arm", "model", "effort")}
        for row in comparisons
        if not row["verbose_protocol_pass"]
    ]
    scope_failures = [
        {key: row[key] for key in ("case_id", "arm", "model", "effort")}
        for row in comparisons
        if not row["verbose_scope_ok"]
    ]
    incomplete_usage = [
        {key: row[key] for key in ("case_id", "arm", "model", "effort")}
        for row in comparisons
        if not row["verbose_usage_complete"]
    ]
    return {
        "schema_version": 1,
        "verified": True,
        "experiment": "v8-verbose-natural-language-vs-v8-mechy",
        "hard_gates": {"task_correctness": "42/42", "treatment_integrity": "42/42"},
        "bindings": {
            "seed": RELEASE_SEED,
            "manifests": {sha: binding["kind"] for sha, binding in bindings.items()},
            "verbose_profile": {"path": _display(verbose_profile), "sha256": profile_sha},
            "verbose_policy": {"path": _display(verbose_policy), "sha256": policy_sha},
            "spark_agent": {"path": _display(SPARK_AGENT), "sha256": spark_sha, "model": SPARK_MODEL, "effort": "medium"},
            "runtime": runtime,
            "verbose_skill_input": next(iter(skill_inputs)),
        },
        "coverage": {
            "planned_invocations": 13,
            "verbose_artifacts": len(verbose_raw_artifacts),
            "verbose_source_artifacts": len(verbose_raw_artifacts),
            "verbose_cells": 42,
            "mechy_cells": 42,
            "excluded_failed_attempts": len(excluded_failed_attempts),
        },
        "primary_parent_token_aggregate": _aggregate(comparisons),
        "parent_token_aggregate_by_arm": by_arm,
        "verbose_spark_efficacy": {
            "forced": _spark_efficacy(comparisons, V8_SPARK_FORCED_ARM),
            "auto": _spark_efficacy(comparisons, V8_SPARK_AUTO_ARM),
        },
        "comparisons": comparisons,
        "disclosures": {
            "protocol_failures": protocol_failures,
            "scope_failures": scope_failures,
            "incomplete_child_usage": incomplete_usage,
            "excluded_failed_attempts": excluded_failed_attempts,
            "child_tokens_are_secondary_and_nullable": True,
            "wall_time": {"publishable": False, "reason": "separate parallel experiment artifacts are contention-affected"},
        },
        "provenance": {
            "release_summary": {"path": _display(release_summary), "sha256": _sha256(release_summary)},
            "mechy_sources": mechy_sources,
            "verbose_sources": verbose_sources,
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--legacy-manifest", type=Path, default=DEFAULT_LEGACY_MANIFEST)
    parser.add_argument("--relay-manifest", type=Path, default=DEFAULT_RELAY_MANIFEST)
    parser.add_argument("--verbose-profile", type=Path, default=DEFAULT_VERBOSE_PROFILE)
    parser.add_argument("--verbose-policy", type=Path, default=DEFAULT_VERBOSE_POLICY)
    parser.add_argument("--verbose-raw", action="append", type=Path, required=True)
    parser.add_argument("--release-summary", type=Path, default=DEFAULT_RELEASE_SUMMARY)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        summary = verify_verbose_experiment(
            manifest=args.manifest,
            legacy_manifest=args.legacy_manifest,
            relay_manifest=args.relay_manifest,
            verbose_profile=args.verbose_profile,
            verbose_policy=args.verbose_policy,
            verbose_raw_artifacts=args.verbose_raw,
            release_summary=args.release_summary,
        )
        write_summary(args.output, summary)
    except VerificationError as error:
        raise SystemExit(f"verbose v8 verification failed: {error}") from error
    print(json.dumps({"verified": True, "output": _display(args.output), "cells": 42}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
