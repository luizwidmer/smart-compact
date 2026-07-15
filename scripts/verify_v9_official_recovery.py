#!/usr/bin/env python3
"""Verify the collision recovery and publish one effective result per official cell."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Sequence

if __package__:
    from . import benchmark_v9_official as benchmark
    from . import verify_v9_official as base
    from .benchmark_agentic import write_json_payload
else:
    import benchmark_v9_official as benchmark
    import verify_v9_official as base
    from benchmark_agentic import write_json_payload


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ORIGINAL = ROOT / "benchmarks/results/raw/v9-official-release.json"
DEFAULT_RECOVERY = ROOT / "benchmarks/results/raw/v9-official-recovery.json"
DEFAULT_ORIGINAL_FREEZE = ROOT / "benchmarks/v9-official-freeze.json"
DEFAULT_RECOVERY_FREEZE = ROOT / "benchmarks/v9-official-recovery-freeze.json"
DEFAULT_CONTROLS = ROOT / "benchmarks/results/v8-release-summary.json"
DEFAULT_OUTPUT = ROOT / "benchmarks/results/v9-official-summary.json"


class VerificationError(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def load(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise VerificationError(f"cannot load {label}: {error}") from error
    require(isinstance(value, dict), f"{label} must be an object")
    return value


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def split_original(
    original: dict[str, Any],
    cells: Sequence[benchmark.CellSpec],
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    require(original.get("benchmark") == "smart-compact-v9-official-completion", "original identity drift")
    require(original.get("complete") is True and original.get("physical_cells") == 12, "original run incomplete")
    rows = original.get("results")
    require(isinstance(rows, list) and len(rows) == 12, "original run needs 12 rows")
    expected = {cell.cell_id for cell in cells}
    by_id: dict[str, dict[str, Any]] = {}
    for row in rows:
        require(isinstance(row, dict) and isinstance(row.get("cell_id"), str), "invalid original row")
        require(row["cell_id"] not in by_id, f"duplicate original row: {row['cell_id']}")
        by_id[row["cell_id"]] = row
    require(set(by_id) == expected, "original cell set mismatch")
    valid: dict[str, dict[str, Any]] = {}
    collisions: dict[str, dict[str, Any]] = {}
    by_cell = {cell.cell_id: cell for cell in cells}
    for cell_id, row in by_id.items():
        error = row.get("runner_error")
        if error is None:
            require(row.get("functional_task_pass") is True, f"{cell_id}: original real run failed")
            try:
                base.validate_result(row, by_cell[cell_id])
            except base.VerificationError as cause:
                raise VerificationError(str(cause)) from cause
            valid[cell_id] = row
            continue
        require(
            isinstance(error, str) and error.startswith("FileExistsError: [Errno 17] File exists:"),
            f"{cell_id}: original failure was not the workspace collision",
        )
        require(row.get("execution_duration_seconds") == 0.0, f"{cell_id}: collision consumed inference time")
        require(row.get("parent_total_tokens") is None, f"{cell_id}: collision has parent usage")
        require(row.get("parent_thread_id") is None, f"{cell_id}: collision started a parent thread")
        collisions[cell_id] = row
    require(len(valid) == 3 and len(collisions) == 9, "expected 3 real rows and 9 collision non-attempts")
    require({row["case_id"] for row in valid.values()} == set(benchmark.CASE_SOURCES), "valid rows need one per case")
    return valid, collisions


def filtered_order(original: dict[str, Any], cell_ids: set[str]) -> list[dict[str, Any]]:
    rows = original.get("execution_order")
    require(isinstance(rows, list), "original execution order missing")
    selected = [row for row in rows if row.get("cell_id") in cell_ids]
    require(len(selected) == len(cell_ids), "recovery execution order incomplete")
    return [{**{key: value for key, value in row.items() if key != "index"}, "index": index} for index, row in enumerate(selected)]


def validate_recovery_freeze(
    freeze: dict[str, Any],
    original: dict[str, Any],
    collisions: dict[str, dict[str, Any]],
) -> None:
    require(freeze.get("schema_version") == 1, "recovery freeze schema drift")
    require(freeze.get("candidate") == "v9-official-collision-recovery", "recovery candidate drift")
    require(freeze.get("status") == "recovery_inputs_frozen_before_inference", "recovery not frozen")
    require(freeze.get("primary_objective") == "parent_total_tokens", "recovery objective drift")
    cells = [
        cell
        for cell in benchmark.build_matrix(benchmark.load_official_cases())
        if cell.cell_id in collisions
    ]
    plan = freeze.get("release_plan")
    require(isinstance(plan, dict), "recovery plan missing")
    require(plan.get("seed") == benchmark.SEED, "recovery seed drift")
    require(plan.get("repetitions_per_cell") == 1, "recovery is not one-pass")
    require(plan.get("jobs") == 4 and plan.get("physical_cells") == 9, "recovery allocation drift")
    require(plan.get("case_universe") == 3, "recovery case count drift")
    require(plan.get("matrix") == benchmark.matrix_rows(cells), "recovery matrix drift")
    require(plan.get("execution_order") == filtered_order(original, set(collisions)), "recovery order drift")
    require(plan.get("recovery_cell_ids") == sorted(collisions), "recovery cell registry drift")
    require(
        plan.get("excluded_valid_cell_ids")
        == sorted(set(cell.cell_id for cell in benchmark.build_matrix(benchmark.load_official_cases())) - set(collisions)),
        "valid-cell exclusion drift",
    )
    require(plan.get("wall_time_policy") == "diagnostic_only_contended_parallel_run", "wall policy drift")
    require(
        freeze.get("release_evidence")
        == {"status": "outputs_excluded_from_input_freeze", "raw_artifacts": [], "verified_cells": 0},
        "recovery freeze includes outputs",
    )
    artifacts = freeze.get("artifacts")
    require(isinstance(artifacts, dict) and artifacts, "recovery artifacts missing")
    for name, artifact in artifacts.items():
        require(isinstance(artifact, dict), f"invalid recovery artifact {name}")
        path = artifact.get("path")
        expected = artifact.get("sha256")
        require(isinstance(path, str) and isinstance(expected, str), f"incomplete artifact {name}")
        target = (ROOT / path).resolve()
        try:
            target.relative_to(ROOT)
        except ValueError as error:
            raise VerificationError(f"artifact escapes repository: {path}") from error
        require(digest(target) == expected, f"recovery artifact drift: {name}")


def verify(
    original_path: Path = DEFAULT_ORIGINAL,
    recovery_path: Path = DEFAULT_RECOVERY,
    *,
    original_freeze_path: Path = DEFAULT_ORIGINAL_FREEZE,
    recovery_freeze_path: Path = DEFAULT_RECOVERY_FREEZE,
    controls_path: Path = DEFAULT_CONTROLS,
) -> dict[str, Any]:
    original = load(original_path, "original collision run")
    recovery = load(recovery_path, "recovery run")
    recovery_freeze = load(recovery_freeze_path, "recovery freeze")
    controls = load(controls_path, "control summary")
    cells = benchmark.build_matrix(benchmark.load_official_cases())
    by_cell = {cell.cell_id: cell for cell in cells}
    valid, collisions = split_original(original, cells)
    validate_recovery_freeze(recovery_freeze, original, collisions)

    require(original.get("freeze_path") == str(original_freeze_path.resolve()), "original freeze path drift")
    require(original.get("freeze_sha256") == digest(original_freeze_path), "original freeze hash drift")
    require(recovery.get("schema_version") == 1, "recovery schema drift")
    require(recovery.get("benchmark") == "smart-compact-v9-official-recovery", "recovery identity drift")
    require(recovery.get("complete") is True, "recovery run incomplete")
    require(recovery.get("physical_cells") == 9, "recovery cell count drift")
    require(recovery.get("repetitions_per_cell") == 1, "recovery is not one-pass")
    require(recovery.get("jobs") == 4 and recovery.get("seed") == benchmark.SEED, "recovery execution drift")
    require(recovery.get("wall_time_contended") is True, "recovery contention disclosure missing")
    require(
        recovery.get("runner_status") == "recovery_matrix_complete_not_release_verdict",
        "recovery runner verdict drift",
    )
    require(
        recovery.get("runner_cleanup") == "per-cell app-server processes closed by context manager",
        "recovery cleanup boundary missing",
    )
    require(recovery.get("original_raw_path") == str(original_path.resolve()), "original raw path mismatch")
    require(recovery.get("original_raw_sha256") == digest(original_path), "original raw hash mismatch")
    require(
        recovery.get("original_freeze_path") == str(original_freeze_path.resolve()),
        "recovery original-freeze path mismatch",
    )
    require(
        recovery.get("original_freeze_sha256") == digest(original_freeze_path),
        "recovery original-freeze hash mismatch",
    )
    require(
        recovery.get("recovery_freeze_path") == str(recovery_freeze_path.resolve()),
        "recovery freeze path mismatch",
    )
    require(recovery.get("recovery_freeze_sha256") == digest(recovery_freeze_path), "recovery freeze hash mismatch")
    require(
        recovery_freeze["artifacts"]["original_failed_raw"]["sha256"] == digest(original_path),
        "frozen original raw mismatch",
    )
    require(
        recovery_freeze["artifacts"]["original_freeze"]["sha256"] == digest(original_freeze_path),
        "frozen original freeze mismatch",
    )
    expected_cells = [cell for cell in cells if cell.cell_id in collisions]
    expected_matrix = benchmark.matrix_rows(expected_cells)
    expected_order = filtered_order(original, set(collisions))
    require(recovery.get("matrix") == expected_matrix, "recovery raw matrix drift")
    require(recovery.get("execution_order") == expected_order, "recovery raw order drift")

    rows = recovery.get("results")
    require(isinstance(rows, list) and len(rows) == 9, "recovery needs 9 rows")
    recovered: dict[str, dict[str, Any]] = {}
    order_index = {row["cell_id"]: row["index"] for row in expected_order}
    for row in rows:
        require(isinstance(row, dict) and isinstance(row.get("cell_id"), str), "invalid recovery row")
        cell_id = row["cell_id"]
        require(cell_id in collisions and cell_id not in recovered, f"unexpected recovery row: {cell_id}")
        try:
            base.validate_result(row, by_cell[cell_id])
        except base.VerificationError as cause:
            raise VerificationError(str(cause)) from cause
        require(row.get("execution_order_index") == order_index[cell_id], f"{cell_id}: recovery order index")
        recovered[cell_id] = row
    require(set(recovered) == set(collisions), "recovery did not replace every collision non-attempt")
    require(recovery.get("functional_task_passes") == 9, "not all recovery tasks passed")
    recovery_protocol = sorted(row["cell_id"] for row in rows if row.get("protocol_pass") is not True)
    require(recovery.get("protocol_misses") == recovery_protocol, "recovery protocol disclosure mismatch")

    effective = {**valid, **recovered}
    require(set(effective) == set(by_cell) and len(effective) == 12, "effective result set is not 12 unique cells")
    indexed_controls = base.control_index(controls)
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
        row = effective[cell.cell_id]
        control = indexed_controls[(cell.case_id, cell.model, cell.effort)]
        standard = int(control["standard_parent_tokens"])
        v6 = int(control["v6_parent_tokens"])
        v8 = int(control["v8_parent_tokens"])
        v9 = int(row["parent_total_tokens"])
        child = int(row["child_total_tokens"])
        spawned = int(row["actual_spawned_workers"])
        best = min(standard, v6, v8)
        table.append(
            {
                "case_id": cell.case_id,
                "task_shape": cell.task_shape,
                "model": cell.model,
                "effort": cell.effort,
                "selected_route": "spark" if cell.arm == benchmark.final.V9_SELECTED_SPARK_ARM else "local",
                "source_run": "original" if cell.cell_id in valid else "collision_recovery",
                "standard_parent_tokens": standard,
                "v6_parent_tokens": v6,
                "v8_parent_tokens": v8,
                "v9_parent_tokens": v9,
                "v9_parent_tokens_saved_vs_standard": standard - v9,
                "v9_parent_reduction_pct_vs_standard": base.pct(standard - v9, standard),
                "v9_parent_tokens_saved_vs_v6": v6 - v9,
                "v9_parent_reduction_pct_vs_v6": base.pct(v6 - v9, v6),
                "v9_parent_tokens_saved_vs_v8": v8 - v9,
                "v9_parent_reduction_pct_vs_v8": base.pct(v8 - v9, v8),
                "v9_parent_tokens_saved_vs_rowwise_prior_oracle": best - v9,
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
        totals["rowwise_prior_oracle_parent_tokens"] += best
    for version in ("standard", "v6", "v8"):
        baseline = totals[f"{version}_parent_tokens"]
        saved = baseline - totals["v9_parent_tokens"]
        totals[f"v9_parent_tokens_saved_vs_{version}"] = saved
        totals[f"v9_parent_reduction_pct_vs_{version}"] = base.pct(saved, baseline)
    oracle = totals["rowwise_prior_oracle_parent_tokens"]
    saved = oracle - totals["v9_parent_tokens"]
    totals["v9_parent_tokens_saved_vs_rowwise_prior_oracle"] = saved
    totals["v9_parent_reduction_pct_vs_rowwise_prior_oracle"] = base.pct(saved, oracle)
    require(
        all(totals["v9_parent_tokens"] < totals[f"{version}_parent_tokens"] for version in ("standard", "v6", "v8")),
        "v9 does not beat every deployable historical version in aggregate parent tokens",
    )

    protocol_misses = sorted(
        row["cell_id"] for row in effective.values() if row.get("protocol_pass") is not True
    )
    telemetry_misses = sorted(
        row["cell_id"] for row in effective.values() if row.get("no_active_children") is not True
    )
    return {
        "schema_version": 1,
        "status": "v9_official_retirement_gate_passed",
        "evidence_status": "fresh_12_unique_inference_cells_across_collision_recovery",
        "original_raw_path": str(original_path.resolve()),
        "original_raw_sha256": digest(original_path),
        "recovery_raw_path": str(recovery_path.resolve()),
        "recovery_raw_sha256": digest(recovery_path),
        "recovery_freeze_path": str(recovery_freeze_path.resolve()),
        "recovery_freeze_sha256": digest(recovery_freeze_path),
        "controls_path": str(controls_path.resolve()),
        "controls_sha256": digest(controls_path),
        "original_real_inference_cells": 3,
        "original_workspace_collision_non_attempts": 9,
        "recovery_real_inference_cells": 9,
        "repeated_real_inference_cells": 0,
        "effective_unique_cells": 12,
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
    parser.add_argument("--original", type=Path, default=DEFAULT_ORIGINAL)
    parser.add_argument("--recovery", type=Path, default=DEFAULT_RECOVERY)
    parser.add_argument("--original-freeze", type=Path, default=DEFAULT_ORIGINAL_FREEZE)
    parser.add_argument("--recovery-freeze", type=Path, default=DEFAULT_RECOVERY_FREEZE)
    parser.add_argument("--controls", type=Path, default=DEFAULT_CONTROLS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    report = verify(
        args.original.expanduser().resolve(),
        args.recovery.expanduser().resolve(),
        original_freeze_path=args.original_freeze.expanduser().resolve(),
        recovery_freeze_path=args.recovery_freeze.expanduser().resolve(),
        controls_path=args.controls.expanduser().resolve(),
    )
    write_json_payload(args.output.expanduser().resolve(), report)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except VerificationError as error:
        print(f"verify-v9-official-recovery: {error}", file=sys.stderr)
        raise SystemExit(1)
