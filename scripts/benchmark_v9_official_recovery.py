#!/usr/bin/env python3
"""Run only the nine official cells skipped by the workspace-collision bug."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Sequence

if __package__:
    from . import benchmark_v8
    from . import benchmark_v9_final as final
    from . import benchmark_v9_official as official
    from .benchmark_agentic import command_version, write_json_payload
    from .open_app_task import AppTaskError, resolve_codex
else:
    import benchmark_v8
    import benchmark_v9_final as final
    import benchmark_v9_official as official
    from benchmark_agentic import command_version, write_json_payload
    from open_app_task import AppTaskError, resolve_codex


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ORIGINAL = ROOT / "benchmarks/results/raw/v9-official-release.json"
DEFAULT_ORIGINAL_FREEZE = ROOT / "benchmarks/v9-official-freeze.json"
DEFAULT_FREEZE = ROOT / "benchmarks/v9-official-recovery-freeze.json"
DEFAULT_OUTPUT = ROOT / "benchmarks/results/raw/v9-official-recovery.json"


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return value


def collision_cells(
    original: dict[str, Any],
    matrix: Sequence[official.CellSpec],
) -> tuple[official.CellSpec, ...]:
    rows = original.get("results")
    if not isinstance(rows, list) or len(rows) != 12:
        raise ValueError("original collision run must contain 12 rows")
    by_id = {row.get("cell_id"): row for row in rows if isinstance(row, dict)}
    if len(by_id) != 12 or set(by_id) != {cell.cell_id for cell in matrix}:
        raise ValueError("original collision result set drift")
    collisions: list[official.CellSpec] = []
    valid = 0
    for cell in matrix:
        row = by_id[cell.cell_id]
        error = row.get("runner_error")
        if error is None:
            if row.get("functional_task_pass") is not True:
                raise ValueError(f"{cell.cell_id}: non-collision task failed")
            valid += 1
            continue
        if not isinstance(error, str) or not error.startswith(
            "FileExistsError: [Errno 17] File exists:"
        ):
            raise ValueError(f"{cell.cell_id}: unexpected original failure")
        if row.get("execution_duration_seconds") != 0.0 or row.get("parent_total_tokens") is not None:
            raise ValueError(f"{cell.cell_id}: collision row contains inference evidence")
        collisions.append(cell)
    if valid != 3 or len(collisions) != 9:
        raise ValueError("recovery requires exactly 3 valid rows and 9 collision non-attempts")
    return tuple(collisions)


def execution_order_rows(
    original: dict[str, Any],
    cells: Sequence[official.CellSpec],
) -> list[dict[str, Any]]:
    selected = {cell.cell_id for cell in cells}
    rows = original.get("execution_order")
    if not isinstance(rows, list):
        raise ValueError("original execution order missing")
    filtered = [row for row in rows if row.get("cell_id") in selected]
    if len(filtered) != len(cells):
        raise ValueError("filtered recovery order is incomplete")
    return [
        {**{key: value for key, value in row.items() if key != "index"}, "index": index}
        for index, row in enumerate(filtered)
    ]


def cell_run_root(run_root: Path, cell: official.CellSpec) -> Path:
    """Give every setting its own namespace before v8 adds case/trial/arm."""
    suffix = hashlib.sha256(cell.cell_id.encode("utf-8")).hexdigest()[:16]
    return run_root / f"cell-{suffix}"


def validate_recovery_freeze(
    path: Path,
    original: dict[str, Any],
    cells: Sequence[official.CellSpec],
) -> dict[str, Any]:
    freeze = load_object(path)
    if freeze.get("schema_version") != 1 or freeze.get("candidate") != "v9-official-collision-recovery":
        raise ValueError("recovery freeze identity drift")
    if freeze.get("status") != "recovery_inputs_frozen_before_inference":
        raise ValueError("recovery inputs were not frozen")
    if freeze.get("primary_objective") != "parent_total_tokens":
        raise ValueError("recovery objective drift")
    all_ids = {cell.cell_id for cell in official.build_matrix(official.load_official_cases())}
    recovery_ids = {cell.cell_id for cell in cells}
    expected_plan = {
        "seed": official.SEED,
        "repetitions_per_cell": 1,
        "jobs": 4,
        "physical_cells": 9,
        "case_universe": 3,
        "matrix": official.matrix_rows(cells),
        "execution_order": execution_order_rows(original, cells),
        "excluded_valid_cell_ids": sorted(all_ids - recovery_ids),
        "recovery_cell_ids": sorted(recovery_ids),
        "wall_time_policy": "diagnostic_only_contended_parallel_run",
    }
    if freeze.get("release_plan") != expected_plan:
        raise ValueError("recovery freeze plan drift")
    if freeze.get("release_evidence") != {
        "status": "outputs_excluded_from_input_freeze",
        "raw_artifacts": [],
        "verified_cells": 0,
    }:
        raise ValueError("recovery freeze includes outputs")
    artifacts = freeze.get("artifacts")
    if not isinstance(artifacts, dict) or not artifacts:
        raise ValueError("recovery freeze artifacts missing")
    for name, artifact in artifacts.items():
        if not isinstance(artifact, dict):
            raise ValueError(f"invalid recovery artifact: {name}")
        relative = artifact.get("path")
        expected = artifact.get("sha256")
        if not isinstance(relative, str) or not isinstance(expected, str):
            raise ValueError(f"incomplete recovery artifact: {name}")
        target = (ROOT / relative).resolve()
        try:
            target.relative_to(ROOT)
        except ValueError as error:
            raise ValueError(f"recovery artifact escapes repository: {relative}") from error
        if hashlib.sha256(target.read_bytes()).hexdigest() != expected:
            raise ValueError(f"recovery artifact drift: {name}")
    return freeze


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original", type=Path, default=DEFAULT_ORIGINAL)
    parser.add_argument("--original-freeze", type=Path, default=DEFAULT_ORIGINAL_FREEZE)
    parser.add_argument("--freeze", type=Path, default=DEFAULT_FREEZE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--seed", type=int, default=official.SEED)
    parser.add_argument("--codex", default=None)
    parser.add_argument("--response-timeout", type=float, default=30.0)
    parser.add_argument("--turn-timeout", type=float, default=900.0)
    parser.add_argument("--drain-timeout", type=float, default=60.0)
    parser.add_argument("--work-root", type=Path, default=None)
    parser.add_argument("--keep-workspaces", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.jobs != 4:
        raise SystemExit("the frozen recovery requires --jobs 4")
    if args.seed != official.SEED:
        raise SystemExit(f"the frozen recovery requires --seed {official.SEED}")
    if args.drain_timeout < 0:
        raise SystemExit("--drain-timeout cannot be negative")
    original_path = args.original.expanduser().resolve()
    original_freeze_path = args.original_freeze.expanduser().resolve()
    recovery_freeze_path = args.freeze.expanduser().resolve()
    original = load_object(original_path)
    cases = official.load_official_cases()
    full_matrix = official.build_matrix(cases)
    cells = collision_cells(original, full_matrix)
    validate_recovery_freeze(recovery_freeze_path, original, cells)
    fixture_validation = benchmark_v8.validate_v8_fixtures(cases)
    if not fixture_validation["ok"]:
        raise SystemExit("fixture validation failed")

    by_id = {case["id"]: case for case in cases}
    order = execution_order_rows(original, cells)
    by_cell = {cell.cell_id: cell for cell in cells}
    jobs_to_run = [by_cell[row["cell_id"]] for row in order]
    rank = {cell.cell_id: index for index, cell in enumerate(cells)}
    run_root = args.work_root.expanduser().resolve() if args.work_root else Path(
        tempfile.mkdtemp(prefix="smart-compact-v9-official-recovery-")
    )
    run_root.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    try:
        with final.configured_final_runner():
            profiles = benchmark_v8.load_arm_profiles(list(official.PHYSICAL_ARMS))
            codex = resolve_codex(args.codex)
            spark_agent = benchmark_v8.validate_v8_spark_agent(
                codex, args.response_timeout, "gpt-5.6-luna"
            )
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = {
                    executor.submit(
                        final._run_cell,
                        cell=cell,
                        case=by_id[cell.case_id],
                        order_index=index,
                        run_root=cell_run_root(run_root, cell),
                        codex=codex,
                        profile=profiles[cell.arm],
                        response_timeout=args.response_timeout,
                        turn_timeout=args.turn_timeout,
                        drain_timeout=args.drain_timeout,
                        keep_workspaces=args.keep_workspaces,
                    ): cell
                    for index, cell in enumerate(jobs_to_run)
                }
                for future in as_completed(futures):
                    result = future.result()
                    result["functional_task_pass"] = official.functional_task_pass(result)
                    results.append(result)
                    results.sort(key=lambda row: rank[row["cell_id"]])
                    write_json_payload(
                        args.output,
                        {
                            "schema_version": 1,
                            "benchmark": "smart-compact-v9-official-recovery",
                            "complete": False,
                            "physical_cells": 9,
                            "repetitions_per_cell": 1,
                            "jobs": 4,
                            "matrix": official.matrix_rows(cells),
                            "execution_order": order,
                            "completed_cells": len(results),
                            "results": results,
                        },
                    )
            functional_passes = sum(official.functional_task_pass(row) for row in results)
            payload = {
                "schema_version": 1,
                "benchmark": "smart-compact-v9-official-recovery",
                "complete": len(results) == 9,
                "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "original_raw_path": str(original_path),
                "original_raw_sha256": hashlib.sha256(original_path.read_bytes()).hexdigest(),
                "original_freeze_path": str(original_freeze_path),
                "original_freeze_sha256": hashlib.sha256(original_freeze_path.read_bytes()).hexdigest(),
                "recovery_freeze_path": str(recovery_freeze_path),
                "recovery_freeze_sha256": hashlib.sha256(recovery_freeze_path.read_bytes()).hexdigest(),
                "physical_cells": 9,
                "repetitions_per_cell": 1,
                "matrix": official.matrix_rows(cells),
                "execution_order": order,
                "fixture_validation": fixture_validation,
                "arm_metadata": benchmark_v8.arm_metadata(list(official.PHYSICAL_ARMS)),
                "spark_agent": spark_agent,
                "codex": codex,
                "codex_version": command_version([codex, "--version"]),
                "rtk_version": command_version(["rtk", "--version"]),
                "seed": args.seed,
                "jobs": 4,
                "wall_time_contended": True,
                "functional_task_passes": functional_passes,
                "task_gate_passes": sum(final.task_gate_pass(row) for row in results),
                "runner_cleanup": "per-cell app-server processes closed by context manager",
                "runner_status": "recovery_matrix_complete_not_release_verdict",
                "protocol_misses": sorted(
                    row["cell_id"] for row in results if row.get("protocol_pass") is not True
                ),
                "results": results,
            }
            write_json_payload(args.output, payload)
            print(json.dumps(payload, indent=2, sort_keys=True))
            return 0 if payload["complete"] and functional_passes == 9 else 1
    finally:
        if not args.keep_workspaces and args.work_root is None:
            shutil.rmtree(run_root, ignore_errors=True)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AppTaskError, OSError, ValueError) as error:
        print(f"benchmark-v9-official-recovery: {error}", file=sys.stderr)
        raise SystemExit(1)
