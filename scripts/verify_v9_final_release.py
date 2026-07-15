#!/usr/bin/env python3
"""Verify the one-pass Smart Compact v9 final release artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any, Iterable, Sequence

if __package__:
    from . import benchmark_v9_final as benchmark
    from .benchmark_agentic import write_json_payload
else:
    import benchmark_v9_final as benchmark
    from benchmark_agentic import write_json_payload


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RAW = ROOT / "benchmarks" / "results" / "raw" / "v9-final-release.json"
DEFAULT_OUTPUT = ROOT / "benchmarks" / "results" / "v9-final-release-summary.json"
DEFAULT_FREEZE = ROOT / "benchmarks" / "v9-final-freeze.json"


class VerificationError(ValueError):
    """Raised when the final artifact violates a release gate."""


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


def _load_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise VerificationError(f"cannot load final raw artifact: {error}") from error
    _require(isinstance(payload, dict), "final raw artifact must be a JSON object")
    return payload


def _digest(value: object, label: str) -> str:
    _require(
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value),
        f"{label} must be a lowercase SHA-256",
    )
    return value


def _validate_treatment(raw: dict[str, Any]) -> None:
    _require(
        raw.get("treatment") == benchmark.FINAL_TREATMENT,
        "final treatment contract drift",
    )


def _expected_arm_metadata() -> dict[str, dict[str, Any]]:
    return {
        benchmark.V6_ARM: {
            "spark_enabled": False,
            "multi_agent": False,
            "routing_mode": "none",
            "profile_path": str(benchmark.V6_PROFILE),
            "policy_path": str(benchmark.V6_POLICY),
            "skill_input": True,
            "policy_sha256": "digest",
        },
        benchmark.V8_ARM: {
            "spark_enabled": False,
            "multi_agent": False,
            "routing_mode": "none",
            "profile_path": str(benchmark.V8_PROFILE),
            "policy_path": str(benchmark.V8_POLICY),
            "skill_input": False,
            "policy_sha256": "digest",
        },
        benchmark.V9_SELECTED_SPARK_ARM: {
            "spark_enabled": True,
            "multi_agent": True,
            "routing_mode": "auto",
            "profile_path": str(benchmark.V9_SPARK_PROFILE),
            "policy_path": None,
            "skill_input": False,
            "policy_sha256": None,
        },
        benchmark.V9_SELECTED_LOCAL_ARM: {
            "spark_enabled": False,
            "multi_agent": False,
            "routing_mode": "none",
            "profile_path": str(benchmark.V9_LOCAL_PROFILE),
            "policy_path": None,
            "skill_input": False,
            "policy_sha256": None,
        },
        benchmark.V9_LOCAL_COUNTERFACTUAL_ARM: {
            "spark_enabled": False,
            "multi_agent": False,
            "routing_mode": "none",
            "profile_path": str(benchmark.V9_LOCAL_PROFILE),
            "policy_path": None,
            "skill_input": False,
            "policy_sha256": None,
        },
    }


def _validate_arm_metadata(raw: dict[str, Any]) -> None:
    observed = raw.get("arm_metadata")
    expected = _expected_arm_metadata()
    _require(isinstance(observed, dict), "arm_metadata is missing")
    _require(set(observed) == set(expected), "arm_metadata arm set mismatch")
    for arm, contract in expected.items():
        row = observed.get(arm)
        _require(isinstance(row, dict), f"missing metadata for {arm}")
        for key, value in contract.items():
            if value == "digest":
                _digest(row.get(key), f"{arm}.{key}")
            else:
                _require(row.get(key) == value, f"{arm}.{key} treatment drift")
        _digest(row.get("profile_sha256"), f"{arm}.profile_sha256")


def _validate_fixture_record(raw: dict[str, Any], case_ids: set[str]) -> None:
    validation = raw.get("fixture_validation")
    _require(isinstance(validation, dict) and validation.get("ok") is True, "fixtures not valid")
    rows = validation.get("cases")
    _require(isinstance(rows, list) and len(rows) == 4, "fixture validation case count mismatch")
    _require({row.get("case_id") for row in rows} == case_ids, "fixture validation IDs mismatch")
    for row in rows:
        _require(isinstance(row, dict), "invalid fixture validation row")
        label = str(row.get("case_id"))
        _require(row.get("ok") is True, f"fixture failed: {label}")
        _require(row.get("reset_reproducible") is True, f"{label}: reset is not reproducible")
        _require(row.get("seed_score_pct") != 100.0, f"{label}: seed unexpectedly passes")
        _require(row.get("gold_score_pct") == 100.0, f"{label}: gold hidden checks failed")
        _require(
            row.get("gold_after_acceptance_score_pct") == 100.0,
            f"{label}: gold acceptance drift",
        )
        _require(row.get("gold_acceptance_ok") is True, f"{label}: gold acceptance failed")
        _require(row.get("gold_scope_ok") is True, f"{label}: gold scope failed")


def _validate_result(row: dict[str, Any], cell: benchmark.CellSpec) -> None:
    label = cell.cell_id
    _require(row.get("cell_id") == label, f"{label}: cell_id mismatch")
    _require(row.get("case_id") == cell.case_id, f"{label}: case mismatch")
    _require(row.get("task_shape") == cell.task_shape, f"{label}: task shape mismatch")
    _require(row.get("arm") == cell.arm, f"{label}: arm mismatch")
    _require(row.get("model") == cell.model, f"{label}: model mismatch")
    _require(row.get("effort") == cell.effort, f"{label}: effort mismatch")
    _require(row.get("trial") == 1, f"{label}: final release is one-pass")
    _require("runner_error" not in row, f"{label}: runner error")
    grade = row.get("grade")
    _require(isinstance(grade, dict), f"{label}: grade missing")
    _require(row.get("task_pass") is True, f"{label}: task correctness failed")
    _require(
        grade.get("ok") is True and grade.get("score_pct") == 100.0,
        f"{label}: exact hidden checks failed",
    )
    _require(row.get("acceptance_observed") is True, f"{label}: acceptance not observed")
    _require(row.get("scope_ok") is True, f"{label}: changed-path scope failed")
    _require(row.get("usage_complete") is True, f"{label}: token usage incomplete")
    _require(row.get("rtk_ok") is True, f"{label}: RTK trace failed")
    _require(row.get("no_active_children") is True, f"{label}: child still active")
    _require(row.get("task_gate_pass") is True, f"{label}: recorded task gate failed")
    parent = _positive_int(row.get("parent_total_tokens"), f"{label}.parent_total_tokens")
    child = _nonnegative_int(row.get("child_total_tokens"), f"{label}.child_total_tokens")
    combined = _positive_int(row.get("combined_total_tokens"), f"{label}.combined_total_tokens")
    _require(combined == parent + child, f"{label}: combined token arithmetic mismatch")
    _nonnegative_int(row.get("actual_spawned_workers"), f"{label}.actual_spawned_workers")
    _nonnegative_int(row.get("useful_worker_count"), f"{label}.useful_worker_count")
    _finite_nonnegative(row.get("execution_duration_seconds"), f"{label}.execution_duration_seconds")


def _validate_worker_contract(row: dict[str, Any], cell: benchmark.CellSpec) -> None:
    label = cell.cell_id
    spawned = int(row["actual_spawned_workers"])
    useful = int(row["useful_worker_count"])
    if cell.arm != benchmark.V9_SELECTED_SPARK_ARM:
        _require(spawned == 0, f"{label}: local/no-Spark treatment spawned a worker")
        _require(useful == 0, f"{label}: local/no-Spark treatment reports useful workers")
        _require(row["child_total_tokens"] == 0, f"{label}: local/no-Spark child tokens")
        _require(not row.get("child_thread_ids"), f"{label}: local/no-Spark child threads")
        return

    _require(cell.task_shape in benchmark.SPARK_SHAPES, f"{label}: Spark shape drift")
    _require(row.get("routing_mode") == "auto", f"{label}: routing mode is not auto")
    _require(spawned >= 1, f"{label}: selected Spark task did not spawn")
    _require(row.get("role_ok") is True, f"{label}: Spark role mismatch")
    _require(row.get("spark_model_ok") is True, f"{label}: Spark model mismatch")
    _require(row.get("spawn_origin_ok") is True, f"{label}: non-parent spawn origin")
    _require(row.get("role_binding_ok") is True, f"{label}: native role binding failed")
    _require(row.get("child_completion_ok") is True, f"{label}: child did not complete")
    child_ids = row.get("child_thread_ids")
    roles = row.get("child_roles")
    records = row.get("spawn_records")
    _require(isinstance(child_ids, list) and len(child_ids) == spawned, f"{label}: child IDs mismatch")
    _require(isinstance(roles, dict) and isinstance(records, dict), f"{label}: worker evidence missing")
    for child_id in child_ids:
        _require(roles.get(child_id) == benchmark.benchmark_v8.SPARK_ROLE, f"{label}: wrong child role")
        record = records.get(child_id)
        _require(isinstance(record, dict), f"{label}: spawn record missing")
        _require(
            record.get("model") == benchmark.benchmark_v8.SPARK_MODEL,
            f"{label}: Spark model drift",
        )
        _require(record.get("origin") == "parent_agent", f"{label}: child origin drift")
        _require(record.get("native_agent_role") is True, f"{label}: role is not native")


def _sum_parent(rows: Iterable[dict[str, Any]]) -> int:
    return sum(int(row["parent_total_tokens"]) for row in rows)


def verify_release(
    raw_path: Path,
    *,
    freeze_path: Path = DEFAULT_FREEZE,
) -> dict[str, Any]:
    raw = _load_object(raw_path)
    _require(raw.get("schema_version") == 1, "raw schema_version must be 1")
    _require(raw.get("benchmark") == "smart-compact-v9-final-release", "benchmark mismatch")
    _require(raw.get("complete") is True, "final matrix is incomplete")
    _require(raw.get("physical_cells") == 14, "final matrix must contain 14 physical cells")
    _require(raw.get("repetitions_per_cell") == 1, "final matrix is not one-pass")
    _require(raw.get("jobs") == 4, "final release must use four-job parallelism")
    _require(raw.get("wall_time_contended") is True, "parallel wall-time contention not disclosed")
    _require(raw.get("seed") == benchmark.SEED, "final seed drift")
    _require(
        raw.get("runner_status") == "matrix_complete_not_release_verdict",
        "runner status must not claim release approval",
    )
    _digest(raw.get("cases_sha256"), "cases_sha256")
    try:
        cells = benchmark.validate_matrix_rows(raw.get("matrix"))
    except ValueError as error:
        raise VerificationError(str(error)) from error
    try:
        freeze = benchmark.validate_release_freeze(
            freeze_path,
            benchmark.DEFAULT_CASES,
            cells,
        )
    except (OSError, json.JSONDecodeError, ValueError) as error:
        raise VerificationError(f"invalid final freeze: {error}") from error
    _require(
        raw.get("execution_order") == freeze["release_plan"]["execution_order"],
        "final execution order drift",
    )
    _require(raw.get("freeze_sha256") == _sha256(freeze_path), "final freeze hash mismatch")
    _require(
        raw.get("freeze_path") == str(freeze_path.resolve()),
        "final freeze path mismatch",
    )
    final_cases = freeze["artifacts"]["final_cases"]
    _require(raw.get("cases_sha256") == final_cases["sha256"], "final cases hash mismatch")
    _require(raw.get("cases_path") == str(benchmark.DEFAULT_CASES.resolve()), "final cases path mismatch")
    _validate_treatment(raw)
    _validate_arm_metadata(raw)
    case_ids = {cell.case_id for cell in cells}
    _validate_fixture_record(raw, case_ids)

    results = raw.get("results")
    _require(isinstance(results, list) and len(results) == 14, "final artifact needs 14 results")
    by_cell: dict[str, dict[str, Any]] = {}
    for row in results:
        _require(isinstance(row, dict), "result row must be an object")
        cell_id = row.get("cell_id")
        _require(isinstance(cell_id, str), "result cell_id missing")
        _require(cell_id not in by_cell, f"duplicate result cell: {cell_id}")
        by_cell[cell_id] = row
    _require(set(by_cell) == {cell.cell_id for cell in cells}, "result cell set mismatch")
    for cell in cells:
        row = by_cell[cell.cell_id]
        _validate_result(row, cell)
        _validate_worker_contract(row, cell)
    expected_order = {
        row["cell_id"]: row["index"] for row in raw["execution_order"]
    }
    for cell_id, row in by_cell.items():
        _require(
            row.get("execution_order_index") == expected_order[cell_id],
            f"{cell_id}: execution order index mismatch",
        )

    index = {(row["case_id"], row["arm"]): row for row in results}
    per_case: list[dict[str, Any]] = []
    v6_rows: list[dict[str, Any]] = []
    v8_rows: list[dict[str, Any]] = []
    selected_rows: list[dict[str, Any]] = []
    counterfactual_rows: list[dict[str, Any]] = []
    for shape in benchmark.TASK_SHAPES:
        case_id = next(cell.case_id for cell in cells if cell.task_shape == shape)
        v6 = index[(case_id, benchmark.V6_ARM)]
        v8 = index[(case_id, benchmark.V8_ARM)]
        selected_arm = (
            benchmark.V9_SELECTED_SPARK_ARM
            if shape in benchmark.SPARK_SHAPES
            else benchmark.V9_SELECTED_LOCAL_ARM
        )
        selected = index[(case_id, selected_arm)]
        counterfactual = (
            index[(case_id, benchmark.V9_LOCAL_COUNTERFACTUAL_ARM)]
            if shape in benchmark.SPARK_SHAPES
            else None
        )
        if counterfactual is not None:
            _require(
                int(selected["parent_total_tokens"])
                < int(counterfactual["parent_total_tokens"]),
                f"{case_id}: selected Spark must strictly beat paired local parent tokens",
            )
            counterfactual_rows.append(counterfactual)
        best_control = min(int(v6["parent_total_tokens"]), int(v8["parent_total_tokens"]))
        spawned = int(selected["actual_spawned_workers"])
        saved = best_control - int(selected["parent_total_tokens"])
        per_case.append(
            {
                "case_id": case_id,
                "task_shape": shape,
                "selected_arm": selected_arm,
                "v6_parent_tokens": int(v6["parent_total_tokens"]),
                "v8_parent_tokens": int(v8["parent_total_tokens"]),
                "selected_v9_parent_tokens": int(selected["parent_total_tokens"]),
                "selected_v9_child_tokens": int(selected["child_total_tokens"]),
                "selected_v9_spawned_workers": spawned,
                "selected_v9_parent_tokens_saved_vs_best_control": saved,
                "selected_v9_parent_tokens_saved_per_spawned_worker": (
                    round(saved / spawned, 3) if spawned else None
                ),
                "local_counterfactual_parent_tokens": (
                    int(counterfactual["parent_total_tokens"])
                    if counterfactual is not None
                    else None
                ),
                "spark_parent_tokens_saved_vs_paired_local": (
                    int(counterfactual["parent_total_tokens"])
                    - int(selected["parent_total_tokens"])
                    if counterfactual is not None
                    else None
                ),
                "spark_parent_tokens_saved_per_spawned_worker": (
                    round(
                        (
                            int(counterfactual["parent_total_tokens"])
                            - int(selected["parent_total_tokens"])
                        )
                        / spawned,
                        3,
                    )
                    if counterfactual is not None and spawned
                    else None
                ),
            }
        )
        v6_rows.append(v6)
        v8_rows.append(v8)
        selected_rows.append(selected)

    totals = {
        "v6_parent_tokens": _sum_parent(v6_rows),
        "v8_parent_tokens": _sum_parent(v8_rows),
        "selected_v9_parent_tokens": _sum_parent(selected_rows),
        "selected_v9_child_tokens": sum(int(row["child_total_tokens"]) for row in selected_rows),
        "selected_v9_spawned_workers": sum(
            int(row["actual_spawned_workers"]) for row in selected_rows
        ),
        "local_counterfactual_parent_tokens": _sum_parent(counterfactual_rows),
    }
    _require(
        totals["selected_v9_parent_tokens"] < totals["v6_parent_tokens"]
        and totals["selected_v9_parent_tokens"] < totals["v8_parent_tokens"],
        "selected v9 must strictly beat both controls in aggregate parent tokens",
    )
    best_control_total = min(totals["v6_parent_tokens"], totals["v8_parent_tokens"])
    saved_total = best_control_total - totals["selected_v9_parent_tokens"]
    spawned_total = totals["selected_v9_spawned_workers"]
    totals["selected_v9_parent_tokens_saved_vs_best_control"] = saved_total
    totals["selected_v9_parent_token_reduction_pct_vs_best_control"] = round(
        saved_total / best_control_total * 100, 3
    )
    spark_selected_rows = [
        row for row in selected_rows if row["arm"] == benchmark.V9_SELECTED_SPARK_ARM
    ]
    spark_pair_saved = _sum_parent(counterfactual_rows) - _sum_parent(spark_selected_rows)
    totals["spark_offload_parent_tokens_saved_vs_paired_local"] = spark_pair_saved
    totals["spark_offload_parent_tokens_saved_per_spawned_worker"] = (
        round(spark_pair_saved / spawned_total, 3) if spawned_total else None
    )
    protocol_misses = sorted(
        row["cell_id"] for row in results if row.get("protocol_pass") is not True
    )
    _require(
        sorted(raw.get("protocol_misses", [])) == protocol_misses,
        "protocol disclosure list is incomplete",
    )
    _require(raw.get("task_gate_passes") == 14, "not all functional task gates passed")
    protocol_fields = (
        "delegation_brief_ok",
        "partition_assignment_syntax_ok",
        "partition_claim_coverage_ok",
        "worker_evidence_coverage_ok",
        "all_spawned_workers_useful",
        "parent_work_replaced_ok",
        "parent_worker_read_overlap_ok",
        "worker_io_ok",
        "routing_ok",
    )
    protocol_miss_details = {
        row["cell_id"]: [field for field in protocol_fields if row.get(field) is False]
        for row in results
        if row["cell_id"] in protocol_misses
    }
    spark_rows = [
        row for row in selected_rows if row["arm"] == benchmark.V9_SELECTED_SPARK_ARM
    ]
    replacement_proven = all(
        row.get("all_spawned_workers_useful") is True
        and row.get("parent_work_replaced_ok") is True
        for row in spark_rows
    )

    return {
        "schema_version": 1,
        "status": "v9_final_release_gate_passed",
        "raw_path": str(raw_path.resolve()),
        "raw_sha256": _sha256(raw_path),
        "freeze_path": str(freeze_path.resolve()),
        "freeze_sha256": _sha256(freeze_path),
        "physical_cells_verified": 14,
        "repetitions_per_cell": 1,
        "task_correct_cells": 14,
        "protocol_misses_nonblocking": protocol_misses,
        "protocol_miss_details": protocol_miss_details,
        "primary_objective": "parent_total_tokens",
        "worker_metric": "spark_offload_parent_tokens_saved_per_spawned_worker",
        "worker_usefulness_protocol_only": True,
        "spark_worker_replacement_evidence": (
            "verified" if replacement_proven else "not_proven_protocol_miss"
        ),
        "worker_cap": None,
        "wall_time_publishable": False,
        "wall_time_reason": "four-job final matrix is intentionally contended; wall metrics are diagnostic",
        "per_case": per_case,
        "totals": totals,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("raw", type=Path, nargs="?", default=DEFAULT_RAW)
    parser.add_argument("--freeze", type=Path, default=DEFAULT_FREEZE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    raw_path = args.raw.expanduser().resolve()
    report = verify_release(
        raw_path,
        freeze_path=args.freeze.expanduser().resolve(),
    )
    write_json_payload(args.output, report)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except VerificationError as error:
        print(f"verify-v9-final-release: {error}", file=sys.stderr)
        raise SystemExit(1)
