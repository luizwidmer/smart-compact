#!/usr/bin/env python3
"""Verify the frozen Smart Compact v9 held-out release artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any, Iterable, Sequence

if __package__:
    from . import benchmark_v9
    from .benchmark_agentic import write_json_payload
else:
    import benchmark_v9
    from benchmark_agentic import write_json_payload


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FREEZE = ROOT / "benchmarks" / "v9-freeze.json"


class VerificationError(ValueError):
    """Raised when a release artifact violates a frozen gate."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _is_int(value: object) -> bool:
    return type(value) is int


def _positive_int(value: object, label: str) -> int:
    _require(_is_int(value) and value > 0, f"{label} must be a positive integer")
    return int(value)


def _nonnegative_int(value: object, label: str) -> int:
    _require(_is_int(value) and value >= 0, f"{label} must be a nonnegative integer")
    return int(value)


def _finite_nonnegative(value: object, label: str) -> float:
    _require(
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
        and float(value) >= 0,
        f"{label} must be finite and nonnegative",
    )
    return float(value)


def _load_object(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise VerificationError(f"cannot load {label}: {error}") from error
    _require(isinstance(payload, dict), f"{label} must be a JSON object")
    return payload


def validate_freeze(path: Path = DEFAULT_FREEZE) -> dict[str, Any]:
    freeze = _load_object(path, "v9 freeze")
    _require(freeze.get("schema_version") == 1, "v9 freeze schema_version must be 1")
    _require(freeze.get("candidate") == "v9", "v9 freeze candidate mismatch")
    _require(
        freeze.get("status") == "release_gate_inputs_frozen_before_inference",
        "v9 release inputs are not frozen",
    )
    _require(freeze.get("primary_objective") == "parent_total_tokens", "objective drift")
    _require(freeze.get("release_plan", {}).get("physical_cells") == 15, "must freeze 15 cells")
    _require(
        freeze.get("release_plan", {}).get("repetitions_per_cell") == 1,
        "v9 release must be one-pass",
    )
    _require(freeze.get("release_plan", {}).get("jobs") == 4, "v9 release jobs drift")
    _require(
        freeze.get("release_plan", {}).get("wall_time_policy")
        == "diagnostic_only_contended_parallel_run",
        "wall-time disclosure policy drift",
    )
    _require(
        freeze.get("release_plan", {}).get("matrix") == benchmark_v9.matrix_rows(),
        "frozen matrix differs from benchmark_v9.MATRIX",
    )
    _require(
        freeze.get("release_plan", {}).get("implementation_reuse_binding")
        == benchmark_v9.IMPLEMENTATION_REUSE_BINDING,
        "implementation reuse binding drift",
    )
    _require(
        freeze.get("release_evidence")
        == {
            "status": "outputs_excluded_from_input_freeze",
            "raw_artifacts": [],
            "verified_cells": 0,
        },
        "release outputs must be excluded from the input freeze",
    )

    artifacts = freeze.get("artifacts")
    _require(isinstance(artifacts, dict) and artifacts, "freeze artifacts are missing")
    for name, artifact in artifacts.items():
        _require(isinstance(artifact, dict), f"invalid frozen artifact {name}")
        relative = artifact.get("path")
        digest = artifact.get("sha256")
        _require(isinstance(relative, str) and relative, f"missing path for {name}")
        _require(isinstance(digest, str) and len(digest) == 64, f"missing sha256 for {name}")
        target = ROOT / relative
        _require(target.is_file(), f"frozen artifact missing: {relative}")
        _require(_sha256(target) == digest, f"frozen artifact drift: {relative}")

    v6 = artifacts["v6_profile"]["sha256"]
    implementation = artifacts["v9_implementation_profile"]["sha256"]
    _require(v6 == implementation, "v6 and v9 implementation profile hashes differ")
    _require(
        (ROOT / artifacts["v6_profile"]["path"]).read_bytes()
        == (ROOT / artifacts["v9_implementation_profile"]["path"]).read_bytes(),
        "v6 and v9 implementation profile bytes differ",
    )
    return freeze


def _expected_arm_metadata(freeze: dict[str, Any]) -> dict[str, dict[str, Any]]:
    artifacts = freeze["artifacts"]
    return {
        benchmark_v9.V6_ARM: {
            "spark_enabled": False,
            "multi_agent": False,
            "routing_mode": "none",
            "profile_sha256": artifacts["v6_profile"]["sha256"],
            "policy_sha256": artifacts["v6_policy"]["sha256"],
            "skill_input": True,
        },
        benchmark_v9.V8_ARM: {
            "spark_enabled": False,
            "multi_agent": False,
            "routing_mode": "none",
            "profile_sha256": artifacts["v8_profile"]["sha256"],
            "policy_sha256": artifacts["v8_policy"]["sha256"],
            "skill_input": False,
        },
        benchmark_v9.V9_NATURAL_ARM: {
            "spark_enabled": False,
            "multi_agent": False,
            "routing_mode": "none",
            "profile_sha256": artifacts["v9_natural_profile"]["sha256"],
            "policy_sha256": None,
            "skill_input": False,
        },
        benchmark_v9.V9_AUTO_ARM: {
            "spark_enabled": True,
            "multi_agent": True,
            "routing_mode": "auto",
            "profile_sha256": artifacts["v9_profile"]["sha256"],
            "policy_sha256": None,
            "skill_input": False,
        },
    }


def _select_lane(selector: dict[str, Any], routing_mode: str, task_shape: str) -> str:
    rules = selector.get("rules")
    _require(isinstance(rules, list) and rules, "selector rules missing")
    dimensions = {"routing_mode": routing_mode, "task_shape": task_shape}
    for rule in rules:
        _require(isinstance(rule, dict), "invalid selector rule")
        when = rule.get("when")
        lane = rule.get("lane")
        _require(isinstance(when, dict) and isinstance(lane, str), "invalid selector rule fields")
        if all(dimensions.get(key) == value for key, value in when.items()):
            return lane
    raise VerificationError(
        f"selector has no rule for routing_mode={routing_mode}, task_shape={task_shape}"
    )


def validate_selector_contract(freeze: dict[str, Any]) -> list[dict[str, str]]:
    artifact = freeze["artifacts"]["optimizer_selection"]
    selector = _load_object(ROOT / artifact["path"], "frozen v9 selector")
    _require(selector.get("schema_version") == 3, "selector schema drift")
    _require(selector.get("product") == "smart-compact-v9", "selector product drift")
    _require(
        selector.get("objective") == "minimize_parent_model_tokens",
        "selector objective drift",
    )
    _require(
        selector.get("selection_stage") == "before_task_creation",
        "selector stage would add in-task prompt state",
    )
    profiles = selector.get("profiles")
    _require(isinstance(profiles, dict), "selector profiles missing")
    expected_profiles = {
        "v9": "smart-compact-v9",
        "v9-implementation": "smart-compact-v9-implementation",
        "v9-natural": "smart-compact-v9-natural",
    }
    _require(
        {lane: profiles.get(lane, {}).get("profile") for lane in expected_profiles}
        == expected_profiles,
        "selector lane-to-profile mapping drift",
    )
    bindings: list[dict[str, str]] = []
    for task_shape in ("implementation", "migration", "handoff", "general"):
        auto_lane = _select_lane(selector, "auto_spark", task_shape)
        _require(auto_lane == "v9", f"{task_shape}: auto must map to canonical v9")
        selected_lane = _select_lane(selector, "no_spark", task_shape)
        expected_lane = "v9-implementation" if task_shape == "implementation" else "v9-natural"
        _require(
            selected_lane == expected_lane,
            f"{task_shape}: no-Spark selected lane drift",
        )
        bindings.append(
            {
                "task_shape": task_shape,
                "auto_lane": auto_lane,
                "auto_physical_arm": benchmark_v9.V9_AUTO_ARM,
                "selected_lane": selected_lane,
                "selected_physical_or_virtual_arm": (
                    benchmark_v9.VIRTUAL_IMPLEMENTATION_ARM
                    if task_shape == "implementation"
                    else benchmark_v9.V9_NATURAL_ARM
                ),
            }
        )
    return bindings


def _validate_arm_metadata(raw: dict[str, Any], freeze: dict[str, Any]) -> None:
    observed = raw.get("arm_metadata")
    expected = _expected_arm_metadata(freeze)
    _require(isinstance(observed, dict), "arm_metadata is missing")
    _require(set(observed) == set(expected), "arm_metadata arm set mismatch")
    for arm, contract in expected.items():
        row = observed.get(arm)
        _require(isinstance(row, dict), f"missing metadata for {arm}")
        for key, value in contract.items():
            _require(row.get(key) == value, f"{arm}.{key} treatment drift")


def _validate_treatment(raw: dict[str, Any]) -> None:
    _require(
        raw.get("treatment")
        == {
            "v9_auto_availability_prompt_injected": False,
            "v9_auto_multi_agent_config": True,
            "forced_spark_included": False,
            "fixed_worker_cap": None,
        },
        "v9 production auto treatment drift",
    )


def _validate_fixture_record(raw: dict[str, Any]) -> None:
    validation = raw.get("fixture_validation")
    _require(isinstance(validation, dict) and validation.get("ok") is True, "fixtures not valid")
    rows = validation.get("cases")
    _require(isinstance(rows, list) and len(rows) == 4, "fixture validation case count mismatch")
    expected = {cell.case_id for cell in benchmark_v9.MATRIX}
    _require({row.get("case_id") for row in rows} == expected, "fixture validation IDs mismatch")
    for row in rows:
        _require(row.get("ok") is True, f"fixture failed: {row.get('case_id')}")
        _require(row.get("reset_reproducible") is True, "fixture reset is not reproducible")
        _require(row.get("seed_score_pct") != 100.0, "seed unexpectedly passes")
        _require(row.get("gold_score_pct") == 100.0, "gold hidden checks failed")
        _require(row.get("gold_after_acceptance_score_pct") == 100.0, "gold acceptance drift")
        _require(row.get("gold_acceptance_ok") is True, "gold acceptance command failed")
        _require(row.get("gold_scope_ok") is True, "gold changes exceed allowed scope")


def _validate_result(row: dict[str, Any], cell: benchmark_v9.CellSpec) -> None:
    label = cell.cell_id
    _require(row.get("cell_id") == label, f"{label}: cell_id mismatch")
    _require(row.get("case_id") == cell.case_id, f"{label}: case mismatch")
    _require(row.get("task_shape") == cell.task_shape, f"{label}: task shape mismatch")
    _require(row.get("arm") == cell.arm, f"{label}: arm mismatch")
    _require(row.get("model") == cell.model, f"{label}: model mismatch")
    _require(row.get("effort") == cell.effort, f"{label}: effort mismatch")
    _require(row.get("trial") == 1, f"{label}: must be the single frozen pass")
    _require("runner_error" not in row, f"{label}: runner error")
    grade = row.get("grade")
    _require(isinstance(grade, dict), f"{label}: grade missing")
    _require(row.get("task_pass") is True, f"{label}: task correctness failed")
    _require(grade.get("ok") is True and grade.get("score_pct") == 100.0, f"{label}: exact hidden checks failed")
    _require(row.get("acceptance_observed") is True, f"{label}: exact acceptance not observed")
    _require(row.get("scope_ok") is True, f"{label}: changed-path scope failed")
    _require(row.get("usage_complete") is True, f"{label}: token usage incomplete")
    _require(row.get("rtk_ok") is True, f"{label}: RTK trace failed")
    _require(row.get("no_active_children") is True, f"{label}: child still active")
    _require(row.get("task_gate_pass") is True, f"{label}: recorded task gate failed")
    _positive_int(row.get("parent_total_tokens"), f"{label}.parent_total_tokens")
    child_tokens = _nonnegative_int(row.get("child_total_tokens"), f"{label}.child_total_tokens")
    combined = _positive_int(row.get("combined_total_tokens"), f"{label}.combined_total_tokens")
    _require(
        combined == row["parent_total_tokens"] + child_tokens,
        f"{label}: combined token arithmetic mismatch",
    )
    _nonnegative_int(row.get("actual_spawned_workers"), f"{label}.actual_spawned_workers")
    _nonnegative_int(row.get("useful_worker_count"), f"{label}.useful_worker_count")
    _finite_nonnegative(row.get("execution_duration_seconds"), f"{label}.execution_duration_seconds")


def _validate_worker_contract(row: dict[str, Any], cell: benchmark_v9.CellSpec) -> None:
    label = cell.cell_id
    spawned = int(row["actual_spawned_workers"])
    useful = int(row["useful_worker_count"])
    if cell.arm != benchmark_v9.V9_AUTO_ARM:
        _require(spawned == 0, f"{label}: no-Spark treatment spawned a worker")
        _require(useful == 0, f"{label}: no-Spark treatment reports a useful worker")
        _require(row["child_total_tokens"] == 0, f"{label}: no-Spark child tokens are nonzero")
        _require(not row.get("child_thread_ids"), f"{label}: no-Spark child threads exist")
        return

    _require(row.get("routing_mode") == "auto", f"{label}: routing mode is not auto")
    required = cell.case_id != "ordered-entitlement-ledger"
    if not required:
        _require(spawned == 0, f"{label}: forbidden general task spawned a worker")
        _require(useful == 0, f"{label}: forbidden general task reports useful workers")
        _require(row["child_total_tokens"] == 0, f"{label}: forbidden task used child tokens")
        _require(not row.get("child_thread_ids"), f"{label}: forbidden task has child threads")
        return

    _require(spawned >= 1, f"{label}: required auto task did not spawn")
    _require(useful == spawned, f"{label}: every spawned worker must be useful")
    _require(row.get("all_spawned_workers_useful") is True, f"{label}: useful-worker gate failed")
    _require(row.get("role_ok") is True, f"{label}: Spark role mismatch")
    _require(row.get("spark_model_ok") is True, f"{label}: Spark model mismatch")
    _require(row.get("spawn_origin_ok") is True, f"{label}: worker did not originate from parent auto routing")
    _require(row.get("role_binding_ok") is True, f"{label}: native role binding failed")
    _require(row.get("child_completion_ok") is True, f"{label}: child did not complete")
    child_ids = row.get("child_thread_ids")
    roles = row.get("child_roles")
    records = row.get("spawn_records")
    _require(isinstance(child_ids, list) and len(child_ids) == spawned, f"{label}: child IDs mismatch")
    _require(isinstance(roles, dict) and isinstance(records, dict), f"{label}: worker evidence missing")
    for child_id in child_ids:
        _require(
            roles.get(child_id) == benchmark_v9.benchmark_v8.SPARK_ROLE,
            f"{label}: child role is not spark_worker",
        )
        record = records.get(child_id)
        _require(isinstance(record, dict), f"{label}: spawn record missing")
        _require(
            record.get("model") == benchmark_v9.benchmark_v8.SPARK_MODEL,
            f"{label}: child model drift",
        )
        _require(record.get("origin") == "parent_agent", f"{label}: child origin drift")
        _require(record.get("native_agent_role") is True, f"{label}: child role is not native")


def _sum_parent(rows: Iterable[dict[str, Any]]) -> int:
    return sum(int(row["parent_total_tokens"]) for row in rows)


def verify_release(
    raw_path: Path,
    *,
    freeze_path: Path = DEFAULT_FREEZE,
) -> dict[str, Any]:
    freeze = validate_freeze(freeze_path)
    selector_bindings = validate_selector_contract(freeze)
    raw = _load_object(raw_path, "v9 raw release artifact")
    _require(raw.get("schema_version") == 1, "raw schema_version must be 1")
    _require(raw.get("benchmark") == "smart-compact-v9-heldout-release", "benchmark mismatch")
    _require(raw.get("complete") is True, "raw matrix is incomplete")
    _require(raw.get("physical_cells") == 15, "raw matrix must contain 15 physical cells")
    _require(raw.get("logical_product_cells") == 16, "logical product cell count mismatch")
    _require(raw.get("repetitions_per_cell") == 1, "raw matrix is not one-pass")
    _require(raw.get("jobs") == 4, "release run must use the frozen four-job parallelism")
    _require(raw.get("wall_time_contended") is True, "parallel wall-time contention not disclosed")
    _require(raw.get("seed") == freeze["release_plan"]["seed"], "seed drift")
    _require(raw.get("matrix") == benchmark_v9.matrix_rows(), "raw matrix contract drift")
    _require(
        raw.get("freeze_sha256") == _sha256(freeze_path),
        "raw artifact does not bind the exact freeze",
    )
    _require(
        raw.get("cases_sha256") == freeze["artifacts"]["heldout_cases"]["sha256"],
        "held-out case hash mismatch",
    )
    _validate_treatment(raw)
    _validate_arm_metadata(raw, freeze)
    _validate_fixture_record(raw)

    binding = raw.get("implementation_reuse_binding")
    _require(isinstance(binding, dict), "implementation reuse binding missing")
    for key, value in benchmark_v9.IMPLEMENTATION_REUSE_BINDING.items():
        _require(binding.get(key) == value, f"implementation binding drift: {key}")
    v6_hash = freeze["artifacts"]["v6_profile"]["sha256"]
    _require(binding.get("v6_sha256") == v6_hash, "binding v6 hash mismatch")
    _require(binding.get("v9_implementation_sha256") == v6_hash, "binding v9 hash mismatch")
    _require(binding.get("equivalence") == "byte_identical_profile", "binding is not exact")

    results = raw.get("results")
    _require(isinstance(results, list), "results must be a list")
    _require(len(results) == 15, "release artifact must have exactly 15 results")
    by_cell: dict[str, dict[str, Any]] = {}
    for row in results:
        _require(isinstance(row, dict), "result row must be an object")
        cell_id = row.get("cell_id")
        _require(isinstance(cell_id, str), "result cell_id missing")
        _require(cell_id not in by_cell, f"duplicate result cell: {cell_id}")
        by_cell[cell_id] = row
    expected_ids = {cell.cell_id for cell in benchmark_v9.MATRIX}
    _require(set(by_cell) == expected_ids, "result cell set differs from frozen matrix")
    for cell in benchmark_v9.MATRIX:
        _validate_result(by_cell[cell.cell_id], cell)
        _validate_worker_contract(by_cell[cell.cell_id], cell)

    index = {(row["case_id"], row["arm"]): row for row in results}
    case_ids = [
        "polyglot-record-normalizer",
        "workspace-permission-migration",
        "incident-window-correlation",
        "ordered-entitlement-ledger",
    ]
    selected_rows: list[dict[str, Any]] = []
    v6_rows: list[dict[str, Any]] = []
    v8_rows: list[dict[str, Any]] = []
    auto_rows: list[dict[str, Any]] = []
    per_case: list[dict[str, Any]] = []
    for case_id in case_ids:
        v6 = index[(case_id, benchmark_v9.V6_ARM)]
        v8 = index[(case_id, benchmark_v9.V8_ARM)]
        auto = index[(case_id, benchmark_v9.V9_AUTO_ARM)]
        selected = (
            v6
            if case_id == "polyglot-record-normalizer"
            else index[(case_id, benchmark_v9.V9_NATURAL_ARM)]
        )
        v6_parent = int(v6["parent_total_tokens"])
        v8_parent = int(v8["parent_total_tokens"])
        selected_parent = int(selected["parent_total_tokens"])
        auto_parent = int(auto["parent_total_tokens"])
        best_control = min(v6_parent, v8_parent)
        v6_wall = float(v6["execution_duration_seconds"])
        v8_wall = float(v8["execution_duration_seconds"])
        auto_wall = float(auto["execution_duration_seconds"])
        best_control_wall = min(v6_wall, v8_wall)
        _require(
            not (auto_parent > best_control and auto_wall > best_control_wall),
            f"{case_id}: v9 auto is worse than controls in both parent tokens and wall time",
        )
        spawned = int(auto["actual_spawned_workers"])
        saved = best_control - auto_parent
        wall_saved = best_control_wall - auto_wall
        useful = int(auto["useful_worker_count"])
        per_case.append(
            {
                "case_id": case_id,
                "v6_parent_tokens": v6_parent,
                "v8_parent_tokens": v8_parent,
                "selected_v9_arm": (
                    benchmark_v9.VIRTUAL_IMPLEMENTATION_ARM
                    if selected is v6
                    else benchmark_v9.V9_NATURAL_ARM
                ),
                "selected_v9_parent_tokens": selected_parent,
                "v9_auto_parent_tokens": auto_parent,
                "v9_auto_spawned_workers": spawned,
                "v9_auto_parent_tokens_saved_vs_best_control": saved,
                "v9_auto_parent_tokens_saved_per_spawned_worker": (
                    round(saved / spawned, 3) if spawned else None
                ),
                "v9_auto_wall_seconds_saved_vs_fastest_control": round(wall_saved, 3),
                "v9_auto_wall_seconds_saved_per_useful_worker": (
                    round(wall_saved / useful, 3) if useful else None
                ),
            }
        )
        v6_rows.append(v6)
        v8_rows.append(v8)
        selected_rows.append(selected)
        auto_rows.append(auto)

    totals = {
        "v6_parent_tokens": _sum_parent(v6_rows),
        "v8_parent_tokens": _sum_parent(v8_rows),
        "selected_v9_parent_tokens": _sum_parent(selected_rows),
        "v9_auto_parent_tokens": _sum_parent(auto_rows),
        "v9_auto_spawned_workers": sum(
            int(row["actual_spawned_workers"]) for row in auto_rows
        ),
        "v9_auto_child_tokens": sum(int(row["child_total_tokens"]) for row in auto_rows),
    }
    _require(
        totals["selected_v9_parent_tokens"] < totals["v6_parent_tokens"]
        and totals["selected_v9_parent_tokens"] < totals["v8_parent_tokens"],
        "selected v9 must strictly beat both retired controls in aggregate parent tokens",
    )
    _require(
        totals["v9_auto_parent_tokens"] < totals["v6_parent_tokens"]
        and totals["v9_auto_parent_tokens"] < totals["v8_parent_tokens"],
        "production v9 auto must strictly beat both retired controls in aggregate parent tokens",
    )
    best_control_total = min(totals["v6_parent_tokens"], totals["v8_parent_tokens"])
    saved_total = best_control_total - totals["v9_auto_parent_tokens"]
    spawned_total = totals["v9_auto_spawned_workers"]
    totals["v9_auto_parent_tokens_saved_vs_best_control"] = saved_total
    totals["v9_auto_parent_token_reduction_pct_vs_best_control"] = round(
        saved_total / best_control_total * 100, 3
    )
    totals["v9_auto_parent_tokens_saved_per_spawned_worker"] = (
        round(saved_total / spawned_total, 3) if spawned_total else None
    )
    fastest_control_wall_total = min(
        sum(float(row["execution_duration_seconds"]) for row in v6_rows),
        sum(float(row["execution_duration_seconds"]) for row in v8_rows),
    )
    auto_wall_total = sum(float(row["execution_duration_seconds"]) for row in auto_rows)
    useful_total = sum(int(row["useful_worker_count"]) for row in auto_rows)
    wall_saved_total = fastest_control_wall_total - auto_wall_total
    totals["v9_auto_wall_seconds"] = round(auto_wall_total, 3)
    totals["v9_auto_wall_seconds_saved_vs_fastest_control"] = round(
        wall_saved_total, 3
    )
    totals["v9_auto_wall_seconds_saved_per_useful_worker"] = (
        round(wall_saved_total / useful_total, 3) if useful_total else None
    )
    protocol_misses = sorted(
        row["cell_id"] for row in results if row.get("protocol_pass") is not True
    )
    _require(
        sorted(raw.get("protocol_misses", [])) == protocol_misses,
        "protocol disclosure list is incomplete",
    )
    _require(raw.get("task_gate_passes") == 15, "not all task gates passed")

    return {
        "schema_version": 1,
        "status": "v9_release_gate_passed",
        "raw_path": str(raw_path.resolve()),
        "raw_sha256": _sha256(raw_path),
        "freeze_path": str(freeze_path.resolve()),
        "freeze_sha256": _sha256(freeze_path),
        "physical_cells_verified": 15,
        "logical_product_cells_verified": 16,
        "implementation_result_reused": True,
        "implementation_additional_inference_cells": 0,
        "selector_bindings": selector_bindings,
        "task_correct_cells": 15,
        "protocol_misses_nonblocking": protocol_misses,
        "primary_objective": "parent_total_tokens",
        "worker_metric": "parent_tokens_saved_per_spawned_worker",
        "worker_cap": None,
        "wall_time_publishable": False,
        "wall_time_reason": "four-job release matrix is intentionally contended; wall metrics are diagnostic",
        "per_case": per_case,
        "totals": totals,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("raw", type=Path)
    parser.add_argument("--freeze", type=Path, default=DEFAULT_FREEZE)
    parser.add_argument("--output", type=Path, default=None)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = verify_release(
        args.raw.expanduser().resolve(),
        freeze_path=args.freeze.expanduser().resolve(),
    )
    if args.output:
        write_json_payload(args.output, report)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except VerificationError as error:
        print(f"verify-v9-release: {error}", file=sys.stderr)
        raise SystemExit(1)
