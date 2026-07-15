#!/usr/bin/env python3
"""Verify v9 on all official rows against frozen Standard, v6, and v8 controls."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any, Sequence

if __package__:
    from . import benchmark_v9_official as benchmark
    from .benchmark_agentic import write_json_payload
else:
    import benchmark_v9_official as benchmark
    from benchmark_agentic import write_json_payload


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RAW = ROOT / "benchmarks/results/raw/v9-official-release.json"
DEFAULT_FREEZE = ROOT / "benchmarks/v9-official-freeze.json"
DEFAULT_CONTROLS = ROOT / "benchmarks/results/v8-release-summary.json"
DEFAULT_OUTPUT = ROOT / "benchmarks/results/v9-official-summary.json"


class VerificationError(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def load_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise VerificationError(f"cannot load {label}: {error}") from error
    require(isinstance(value, dict), f"{label} must be an object")
    return value


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def positive(value: object, label: str) -> int:
    require(type(value) is int and value > 0, f"{label} must be a positive integer")
    return int(value)


def nonnegative(value: object, label: str) -> int:
    require(type(value) is int and value >= 0, f"{label} must be a nonnegative integer")
    return int(value)


def pct(saved: int, baseline: int) -> float:
    return round(saved / baseline * 100, 3)


def control_index(controls: dict[str, Any]) -> dict[tuple[str, str, str], dict[str, Any]]:
    require(controls.get("schema_version") == 3, "control schema drift")
    require(controls.get("verified") is True, "controls are not verified")
    rows = controls.get("parent_token_table")
    require(isinstance(rows, list) and len(rows) == 12, "controls need 12 rows")
    expected = {
        (case_id, model, effort)
        for case_id in benchmark.CASE_SOURCES
        for model, effort in benchmark.SETTINGS
    }
    indexed: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in rows:
        require(isinstance(row, dict), "control row must be an object")
        key = (row.get("scope"), row.get("model"), row.get("effort"))
        require(key in expected and key not in indexed, f"invalid control row: {key}")
        correctness = row.get("correctness")
        require(
            isinstance(correctness, dict)
            and all(correctness.get(name) is True for name in ("standard", "v6", "v8")),
            f"{key}: control correctness failed",
        )
        for field in ("standard_parent_tokens", "v6_parent_tokens", "v8_parent_tokens"):
            positive(row.get(field), f"{key}.{field}")
        require(row.get("v8_arm") == "v8-no-spark", f"{key}: v8 is not no-Spark")
        indexed[key] = row
    require(set(indexed) == expected, "control row set mismatch")
    return indexed


def validate_fixtures(raw: dict[str, Any]) -> None:
    validation = raw.get("fixture_validation")
    require(isinstance(validation, dict) and validation.get("ok") is True, "fixtures failed")
    rows = validation.get("cases")
    require(isinstance(rows, list) and len(rows) == 3, "fixture count mismatch")
    require({row.get("case_id") for row in rows} == set(benchmark.CASE_SOURCES), "fixture IDs mismatch")
    for row in rows:
        label = str(row.get("case_id"))
        require(isinstance(row, dict) and row.get("ok") is True, f"{label}: fixture failed")
        require(row.get("reset_reproducible") is True, f"{label}: reset failed")
        require(row.get("seed_score_pct") != 100.0, f"{label}: seed passes")
        require(row.get("gold_score_pct") == 100.0, f"{label}: gold failed")
        require(row.get("gold_after_acceptance_score_pct") == 100.0, f"{label}: gold drift")
        require(row.get("gold_acceptance_ok") is True, f"{label}: acceptance failed")
        require(row.get("gold_scope_ok") is True, f"{label}: scope failed")


def validate_result(row: dict[str, Any], cell: benchmark.CellSpec) -> None:
    label = cell.cell_id
    expected = {
        "cell_id": label,
        "case_id": cell.case_id,
        "task_shape": cell.task_shape,
        "arm": cell.arm,
        "model": cell.model,
        "effort": cell.effort,
        "trial": 1,
    }
    for key, value in expected.items():
        require(row.get(key) == value, f"{label}: {key} mismatch")
    require("runner_error" not in row, f"{label}: runner error")
    grade = row.get("grade")
    require(row.get("task_pass") is True, f"{label}: task failed")
    require(row.get("functional_task_pass") is True, f"{label}: functional gate failed")
    require(
        isinstance(grade, dict) and grade.get("ok") is True and grade.get("score_pct") == 100.0,
        f"{label}: hidden checks failed",
    )
    for field in ("acceptance_observed", "scope_ok", "usage_complete", "rtk_ok"):
        require(row.get(field) is True, f"{label}: {field} failed")
    parent = positive(row.get("parent_total_tokens"), f"{label}.parent")
    child = nonnegative(row.get("child_total_tokens"), f"{label}.child")
    require(row.get("combined_total_tokens") == parent + child, f"{label}: token arithmetic")
    spawned = nonnegative(row.get("actual_spawned_workers"), f"{label}.spawned")
    useful = nonnegative(row.get("useful_worker_count"), f"{label}.useful")
    duration = row.get("execution_duration_seconds")
    require(
        isinstance(duration, (int, float))
        and not isinstance(duration, bool)
        and math.isfinite(float(duration))
        and duration >= 0,
        f"{label}: invalid duration",
    )
    child_ids = row.get("child_thread_ids")
    require(isinstance(child_ids, list), f"{label}: child IDs missing")
    if cell.arm == benchmark.final.V9_SELECTED_LOCAL_ARM:
        require(spawned == useful == child == 0, f"{label}: local route spawned or spent child tokens")
        require(child_ids == [], f"{label}: local route has child IDs")
        require(row.get("no_active_children") is True, f"{label}: local child active")
        require(row.get("task_gate_pass") is True, f"{label}: local full gate failed")
    else:
        require(cell.task_shape == "implementation" and spawned >= 1, f"{label}: Spark routing failed")
        require(len(child_ids) == spawned, f"{label}: worker telemetry mismatch")
        if row.get("no_active_children") is not True:
            errors = row.get("child_read_errors")
            require(
                isinstance(errors, dict)
                and errors
                and all("ephemeral threads do not support includeTurns" in str(value) for value in errors.values()),
                f"{label}: unexplained active-child telemetry",
            )


def verify_release(
    raw_path: Path,
    *,
    freeze_path: Path = DEFAULT_FREEZE,
    controls_path: Path = DEFAULT_CONTROLS,
) -> dict[str, Any]:
    raw = load_object(raw_path, "official raw artifact")
    freeze = load_object(freeze_path, "official freeze")
    controls = load_object(controls_path, "control summary")
    cells = benchmark.build_matrix(benchmark.load_official_cases())
    try:
        benchmark.validate_release_freeze(freeze_path, cells)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        raise VerificationError(str(error)) from error

    expected_top = {
        "schema_version": 1,
        "benchmark": "smart-compact-v9-official-completion",
        "complete": True,
        "physical_cells": 12,
        "repetitions_per_cell": 1,
        "jobs": 4,
        "seed": benchmark.SEED,
        "wall_time_contended": True,
        "treatment": benchmark.OFFICIAL_TREATMENT,
        "runner_status": "matrix_complete_not_release_verdict",
        "runner_cleanup": "per-cell app-server processes closed by context manager",
    }
    for key, value in expected_top.items():
        require(raw.get(key) == value, f"official raw {key} drift")
    require(raw.get("freeze_path") == str(freeze_path.resolve()), "freeze path mismatch")
    require(raw.get("freeze_sha256") == sha256(freeze_path), "freeze hash mismatch")
    require(raw.get("control_summary_path") == str(controls_path.resolve()), "control path mismatch")
    require(raw.get("control_summary_sha256") == sha256(controls_path), "control hash mismatch")
    require(
        freeze["artifacts"]["v8_control_summary"]["sha256"] == sha256(controls_path),
        "frozen control hash mismatch",
    )

    sources = benchmark.source_rows()
    require(raw.get("case_sources") == sources, "case-source binding mismatch")
    artifact_names = {
        "legacy-calculator": "calculator_cases",
        "legacy-relay-bench": "relay_cases",
        "monorepo-sdk-migration": "confirmation_cases",
    }
    for source in sources:
        require(
            freeze["artifacts"][artifact_names[source["case_id"]]]["sha256"] == source["sha256"],
            f"{source['case_id']}: frozen source mismatch",
        )

    matrix = benchmark.matrix_rows(cells)
    order = benchmark.execution_order_rows(cells)
    require(raw.get("matrix") == matrix == freeze["release_plan"]["matrix"], "matrix drift")
    require(raw.get("execution_order") == order == freeze["release_plan"]["execution_order"], "order drift")
    validate_fixtures(raw)

    results = raw.get("results")
    require(isinstance(results, list) and len(results) == 12, "official raw needs 12 results")
    by_cell: dict[str, dict[str, Any]] = {}
    for row in results:
        require(isinstance(row, dict) and isinstance(row.get("cell_id"), str), "invalid result row")
        require(row["cell_id"] not in by_cell, f"duplicate result: {row['cell_id']}")
        by_cell[row["cell_id"]] = row
    require(set(by_cell) == {cell.cell_id for cell in cells}, "result cell set mismatch")
    order_index = {row["cell_id"]: row["index"] for row in order}
    for cell in cells:
        row = by_cell[cell.cell_id]
        validate_result(row, cell)
        require(row.get("execution_order_index") == order_index[cell.cell_id], f"{cell.cell_id}: order index")
    require(raw.get("functional_task_passes") == 12, "not all official tasks passed")

    protocol_misses = sorted(row["cell_id"] for row in results if row.get("protocol_pass") is not True)
    require(raw.get("protocol_misses") == protocol_misses, "protocol disclosure mismatch")
    indexed_controls = control_index(controls)
    table: list[dict[str, Any]] = []
    totals = {
        "standard_parent_tokens": 0,
        "v6_parent_tokens": 0,
        "v8_parent_tokens": 0,
        "v9_parent_tokens": 0,
        "v9_child_tokens": 0,
        "v9_spawned_workers": 0,
        "rowwise_prior_oracle_parent_tokens": 0,
    }
    for cell in cells:
        result = by_cell[cell.cell_id]
        control = indexed_controls[(cell.case_id, cell.model, cell.effort)]
        standard = int(control["standard_parent_tokens"])
        v6 = int(control["v6_parent_tokens"])
        v8 = int(control["v8_parent_tokens"])
        v9 = int(result["parent_total_tokens"])
        child = int(result["child_total_tokens"])
        spawned = int(result["actual_spawned_workers"])
        best_prior = min(standard, v6, v8)
        table.append(
            {
                "case_id": cell.case_id,
                "task_shape": cell.task_shape,
                "model": cell.model,
                "effort": cell.effort,
                "selected_route": "spark" if cell.arm == benchmark.final.V9_SELECTED_SPARK_ARM else "local",
                "standard_parent_tokens": standard,
                "v6_parent_tokens": v6,
                "v8_parent_tokens": v8,
                "v9_parent_tokens": v9,
                "v9_parent_tokens_saved_vs_standard": standard - v9,
                "v9_parent_reduction_pct_vs_standard": pct(standard - v9, standard),
                "v9_parent_tokens_saved_vs_v6": v6 - v9,
                "v9_parent_reduction_pct_vs_v6": pct(v6 - v9, v6),
                "v9_parent_tokens_saved_vs_v8": v8 - v9,
                "v9_parent_reduction_pct_vs_v8": pct(v8 - v9, v8),
                "v9_parent_tokens_saved_vs_rowwise_prior_oracle": best_prior - v9,
                "v9_child_tokens": child,
                "v9_spawned_workers": spawned,
                "task_correct": True,
            }
        )
        totals["standard_parent_tokens"] += standard
        totals["v6_parent_tokens"] += v6
        totals["v8_parent_tokens"] += v8
        totals["v9_parent_tokens"] += v9
        totals["v9_child_tokens"] += child
        totals["v9_spawned_workers"] += spawned
        totals["rowwise_prior_oracle_parent_tokens"] += best_prior

    for version in ("standard", "v6", "v8"):
        baseline = totals[f"{version}_parent_tokens"]
        saved = baseline - totals["v9_parent_tokens"]
        totals[f"v9_parent_tokens_saved_vs_{version}"] = saved
        totals[f"v9_parent_reduction_pct_vs_{version}"] = pct(saved, baseline)
    oracle = totals["rowwise_prior_oracle_parent_tokens"]
    oracle_saved = oracle - totals["v9_parent_tokens"]
    totals["v9_parent_tokens_saved_vs_rowwise_prior_oracle"] = oracle_saved
    totals["v9_parent_reduction_pct_vs_rowwise_prior_oracle"] = pct(oracle_saved, oracle)
    require(
        all(
            totals["v9_parent_tokens"] < totals[f"{version}_parent_tokens"]
            for version in ("standard", "v6", "v8")
        ),
        "v9 does not beat every deployable historical version in aggregate parent tokens",
    )
    telemetry_misses = sorted(
        row["cell_id"] for row in results if row.get("no_active_children") is not True
    )
    return {
        "schema_version": 1,
        "status": "v9_official_retirement_gate_passed",
        "evidence_status": "fresh_v9_official_completion_against_reused_verified_controls",
        "raw_path": str(raw_path.resolve()),
        "raw_sha256": sha256(raw_path),
        "freeze_path": str(freeze_path.resolve()),
        "freeze_sha256": sha256(freeze_path),
        "controls_path": str(controls_path.resolve()),
        "controls_sha256": sha256(controls_path),
        "physical_cells_verified": 12,
        "repetitions_per_cell": 1,
        "task_correct_cells": 12,
        "protocol_misses_nonblocking": protocol_misses,
        "ephemeral_child_completion_telemetry_misses_nonblocking": telemetry_misses,
        "actual_process_cleanup": "verified_by_per_cell_app_server_context_exit",
        "primary_objective": "parent_total_tokens",
        "worker_cap": None,
        "wall_time_publishable": False,
        "comparison_table": table,
        "totals": totals,
        "rowwise_prior_oracle_is_deployable_version": False,
        "retirement_gate": "v9 aggregate must strictly beat Standard, v6, and v8",
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("raw", type=Path, nargs="?", default=DEFAULT_RAW)
    parser.add_argument("--freeze", type=Path, default=DEFAULT_FREEZE)
    parser.add_argument("--controls", type=Path, default=DEFAULT_CONTROLS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    report = verify_release(
        args.raw.expanduser().resolve(),
        freeze_path=args.freeze.expanduser().resolve(),
        controls_path=args.controls.expanduser().resolve(),
    )
    write_json_payload(args.output.expanduser().resolve(), report)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except VerificationError as error:
        print(f"verify-v9-official: {error}", file=sys.stderr)
        raise SystemExit(1)
