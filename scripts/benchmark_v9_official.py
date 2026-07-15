#!/usr/bin/env python3
"""Run the frozen 12-cell v9 completion over the three official benchmarks."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import shutil
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Sequence

if __package__:
    from . import benchmark_v8
    from . import benchmark_v9_final as final
    from .benchmark_agentic import command_version, write_json_payload
    from .open_app_task import AppTaskError, resolve_codex
else:
    import benchmark_v8
    import benchmark_v9_final as final
    from benchmark_agentic import command_version, write_json_payload
    from open_app_task import AppTaskError, resolve_codex


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FREEZE = ROOT / "benchmarks" / "v9-official-freeze.json"
DEFAULT_OUTPUT = ROOT / "benchmarks" / "results" / "raw" / "v9-official-release.json"
CONTROL_SUMMARY = ROOT / "benchmarks" / "results" / "v8-release-summary.json"
CASE_SOURCES = {
    "legacy-calculator": ROOT / "benchmarks" / "agentic-v8-legacy-calculator.json",
    "legacy-relay-bench": ROOT / "benchmarks" / "agentic-v8-legacy-relay-bench.json",
    "monorepo-sdk-migration": ROOT / "benchmarks" / "agentic-v8-confirmation.json",
}
CASE_SHAPES = {
    "legacy-calculator": "implementation",
    "legacy-relay-bench": "handoff",
    "monorepo-sdk-migration": "migration",
}
CASE_ARMS = {
    "legacy-calculator": final.V9_SELECTED_SPARK_ARM,
    "legacy-relay-bench": final.V9_SELECTED_LOCAL_ARM,
    "monorepo-sdk-migration": final.V9_SELECTED_LOCAL_ARM,
}
SETTINGS = (
    ("gpt-5.6-sol", "medium"),
    ("gpt-5.6-sol", "high"),
    ("gpt-5.6-luna", "xhigh"),
    ("gpt-5.6-luna", "max"),
)
PHYSICAL_ARMS = (final.V9_SELECTED_SPARK_ARM, final.V9_SELECTED_LOCAL_ARM)
SEED = 20260716
OFFICIAL_TREATMENT = {
    "availability_prompt_injected": False,
    "fixed_worker_cap": None,
    "implementation_route": "spark",
    "handoff_route": "local",
    "migration_route": "local",
    "local_multi_agent_config": False,
    "spark_multi_agent_config": True,
    "smart_compact_skill_active_during_package_work": False,
}


@dataclass(frozen=True)
class CellSpec:
    case_id: str
    task_shape: str
    arm: str
    model: str
    effort: str

    @property
    def cell_id(self) -> str:
        return f"{self.case_id}::{self.model}::{self.effort}::{self.arm}"


def load_official_cases() -> list[dict[str, Any]]:
    """Load exactly one named case from each immutable official manifest."""
    cases: list[dict[str, Any]] = []
    for case_id, source in CASE_SOURCES.items():
        matches = [case for case in benchmark_v8.load_cases(source) if case.get("id") == case_id]
        if len(matches) != 1:
            raise ValueError(f"{source}: expected exactly one {case_id} case")
        cases.append(matches[0])
    return cases


def source_rows() -> list[dict[str, str]]:
    return [
        {
            "case_id": case_id,
            "path": str(path.resolve()),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
        for case_id, path in CASE_SOURCES.items()
    ]


def build_matrix(cases: Sequence[dict[str, Any]]) -> tuple[CellSpec, ...]:
    observed = [case.get("id") for case in cases]
    if len(observed) != 3 or set(observed) != set(CASE_SOURCES) or len(set(observed)) != 3:
        raise ValueError("official completion requires exactly the three frozen official cases")
    cells: list[CellSpec] = []
    for case_id in CASE_SOURCES:
        for model, effort in SETTINGS:
            cells.append(
                CellSpec(
                    case_id=case_id,
                    task_shape=CASE_SHAPES[case_id],
                    arm=CASE_ARMS[case_id],
                    model=model,
                    effort=effort,
                )
            )
    return tuple(cells)


def matrix_rows(cells: Sequence[CellSpec]) -> list[dict[str, str]]:
    return [{**asdict(cell), "cell_id": cell.cell_id} for cell in cells]


def validate_matrix_rows(rows: object) -> tuple[CellSpec, ...]:
    if not isinstance(rows, list) or len(rows) != 12:
        raise ValueError("official v9 matrix must contain exactly 12 cells")
    expected_keys = {"case_id", "task_shape", "arm", "model", "effort", "cell_id"}
    cells: list[CellSpec] = []
    for row in rows:
        if not isinstance(row, dict) or set(row) != expected_keys:
            raise ValueError("invalid official v9 matrix row")
        values = [row.get(key) for key in ("case_id", "task_shape", "arm", "model", "effort")]
        if not all(isinstance(value, str) and value for value in values):
            raise ValueError("official v9 matrix fields must be non-empty strings")
        cell = CellSpec(*values)
        if row.get("cell_id") != cell.cell_id:
            raise ValueError(f"{cell.cell_id}: matrix cell_id mismatch")
        cells.append(cell)
    if len({cell.cell_id for cell in cells}) != 12:
        raise ValueError("official v9 matrix cell IDs must be unique")
    expected = build_matrix(load_official_cases())
    if tuple(cells) != expected:
        raise ValueError("official v9 matrix treatment or setting drift")
    return tuple(cells)


def execution_order_rows(cells: Sequence[CellSpec], seed: int = SEED) -> list[dict[str, Any]]:
    shuffled = list(cells)
    random.Random(seed).shuffle(shuffled)
    return [
        {"index": index, **matrix_rows((cell,))[0]}
        for index, cell in enumerate(shuffled)
    ]


def functional_task_pass(result: dict[str, Any]) -> bool:
    grade = result.get("grade")
    parent = result.get("parent_total_tokens")
    return bool(
        result.get("task_pass")
        and isinstance(grade, dict)
        and grade.get("ok")
        and grade.get("score_pct") == 100.0
        and result.get("scope_ok")
        and result.get("acceptance_observed")
        and result.get("usage_complete")
        and result.get("rtk_ok")
        and type(parent) is int
        and parent > 0
    )


def validate_release_freeze(path: Path, matrix: Sequence[CellSpec]) -> dict[str, Any]:
    freeze = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(freeze, dict):
        raise ValueError("official freeze must be a JSON object")
    if freeze.get("schema_version") != 1 or freeze.get("candidate") != "v9-official-completion":
        raise ValueError("official freeze identity drift")
    if freeze.get("status") != "official_inputs_frozen_before_inference":
        raise ValueError("official inputs were not frozen before inference")
    if freeze.get("primary_objective") != "parent_total_tokens":
        raise ValueError("official freeze objective drift")
    if freeze.get("treatment") != OFFICIAL_TREATMENT:
        raise ValueError("official freeze treatment drift")
    expected_plan = {
        "seed": SEED,
        "repetitions_per_cell": 1,
        "jobs": 4,
        "physical_cells": 12,
        "case_universe": 3,
        "matrix": matrix_rows(matrix),
        "execution_order": execution_order_rows(matrix),
        "release_cell_allocation": {
            final.V9_SELECTED_SPARK_ARM: 4,
            final.V9_SELECTED_LOCAL_ARM: 8,
        },
        "settings": [list(setting) for setting in SETTINGS],
        "wall_time_policy": "diagnostic_only_contended_parallel_run",
    }
    if freeze.get("release_plan") != expected_plan:
        raise ValueError("official freeze plan drift")
    if freeze.get("release_evidence") != {
        "status": "outputs_excluded_from_input_freeze",
        "raw_artifacts": [],
        "verified_cells": 0,
    }:
        raise ValueError("official freeze must exclude outputs")
    artifacts = freeze.get("artifacts")
    if not isinstance(artifacts, dict) or not artifacts:
        raise ValueError("official freeze artifacts missing")
    for name, artifact in artifacts.items():
        if not isinstance(artifact, dict):
            raise ValueError(f"invalid frozen artifact {name}")
        relative = artifact.get("path")
        digest = artifact.get("sha256")
        if not isinstance(relative, str) or not isinstance(digest, str):
            raise ValueError(f"incomplete frozen artifact {name}")
        target = (ROOT / relative).resolve()
        try:
            target.relative_to(ROOT)
        except ValueError as error:
            raise ValueError(f"frozen artifact escapes repository: {relative}") from error
        if hashlib.sha256(target.read_bytes()).hexdigest() != digest:
            raise ValueError(f"official frozen artifact drift: {name}")
    return freeze


def _checkpoint(
    matrix: Sequence[CellSpec],
    results: list[dict[str, Any]],
    execution_order: list[dict[str, Any]],
    jobs: int,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "benchmark": "smart-compact-v9-official-completion",
        "complete": False,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "physical_cells": 12,
        "repetitions_per_cell": 1,
        "jobs": jobs,
        "matrix": matrix_rows(matrix),
        "execution_order": execution_order,
        "completed_cells": len(results),
        "results": results,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze", type=Path, default=DEFAULT_FREEZE)
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--codex", default=None)
    parser.add_argument("--response-timeout", type=float, default=30.0)
    parser.add_argument("--turn-timeout", type=float, default=900.0)
    parser.add_argument("--drain-timeout", type=float, default=60.0)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--work-root", type=Path, default=None)
    parser.add_argument("--keep-workspaces", action="store_true")
    parser.add_argument("--validate-fixtures", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.jobs < 1:
        raise SystemExit("--jobs must be at least 1")
    if not args.validate_fixtures and args.jobs != 4:
        raise SystemExit("the frozen official completion requires --jobs 4")
    if not args.validate_fixtures and args.seed != SEED:
        raise SystemExit(f"the frozen official completion requires --seed {SEED}")
    if args.drain_timeout < 0:
        raise SystemExit("--drain-timeout cannot be negative")

    cases = load_official_cases()
    matrix = build_matrix(cases)
    fixture_validation = benchmark_v8.validate_v8_fixtures(cases)
    if args.validate_fixtures:
        print(json.dumps(fixture_validation, indent=2, sort_keys=True))
        return 0 if fixture_validation["ok"] else 1
    if not fixture_validation["ok"]:
        raise SystemExit("fixture validation failed")

    freeze_path = args.freeze.expanduser().resolve()
    validate_release_freeze(freeze_path, matrix)
    by_id = {case["id"]: case for case in cases}
    run_root = args.work_root.expanduser().resolve() if args.work_root else Path(
        tempfile.mkdtemp(prefix="smart-compact-v9-official-")
    )
    run_root.mkdir(parents=True, exist_ok=True)
    order = execution_order_rows(matrix, args.seed)
    by_cell = {cell.cell_id: cell for cell in matrix}
    jobs_to_run = [by_cell[row["cell_id"]] for row in order]
    jobs_used = min(args.jobs, len(jobs_to_run))
    rank = {cell.cell_id: index for index, cell in enumerate(matrix)}
    results: list[dict[str, Any]] = []

    try:
        with final.configured_final_runner():
            profiles = benchmark_v8.load_arm_profiles(list(PHYSICAL_ARMS))
            codex = resolve_codex(args.codex)
            spark_agent = benchmark_v8.validate_v8_spark_agent(
                codex, args.response_timeout, "gpt-5.6-luna"
            )
            with ThreadPoolExecutor(max_workers=jobs_used) as executor:
                futures = {
                    executor.submit(
                        final._run_cell,
                        cell=cell,
                        case=by_id[cell.case_id],
                        order_index=index,
                        run_root=run_root,
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
                    result["functional_task_pass"] = functional_task_pass(result)
                    results.append(result)
                    results.sort(key=lambda row: rank[row["cell_id"]])
                    write_json_payload(
                        args.output,
                        _checkpoint(matrix, results, order, jobs_used),
                    )

            functional_passes = sum(functional_task_pass(row) for row in results)
            payload = {
                "schema_version": 1,
                "benchmark": "smart-compact-v9-official-completion",
                "complete": len(results) == 12,
                "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "case_sources": source_rows(),
                "control_summary_path": str(CONTROL_SUMMARY.resolve()),
                "control_summary_sha256": hashlib.sha256(CONTROL_SUMMARY.read_bytes()).hexdigest(),
                "freeze_path": str(freeze_path),
                "freeze_sha256": hashlib.sha256(freeze_path.read_bytes()).hexdigest(),
                "physical_cells": 12,
                "repetitions_per_cell": 1,
                "matrix": matrix_rows(matrix),
                "treatment": OFFICIAL_TREATMENT,
                "arm_metadata": benchmark_v8.arm_metadata(list(PHYSICAL_ARMS)),
                "disabled_skill_path": str(benchmark_v8.INSTALLED_SKILL),
                "spark_agent": spark_agent,
                "codex": codex,
                "codex_version": command_version([codex, "--version"]),
                "rtk_version": command_version(["rtk", "--version"]),
                "seed": args.seed,
                "jobs": jobs_used,
                "wall_time_contended": jobs_used > 1,
                "execution_order": order,
                "fixture_validation": fixture_validation,
                "functional_task_passes": functional_passes,
                "task_gate_passes": sum(final.task_gate_pass(row) for row in results),
                "runner_cleanup": "per-cell app-server processes closed by context manager",
                "runner_status": "matrix_complete_not_release_verdict",
                "protocol_misses": sorted(
                    row["cell_id"] for row in results if row.get("protocol_pass") is not True
                ),
                "results": results,
            }
            write_json_payload(args.output, payload)
            print(json.dumps(payload, indent=2, sort_keys=True))
            return 0 if payload["complete"] and functional_passes == 12 else 1
    finally:
        if not args.keep_workspaces and args.work_root is None:
            shutil.rmtree(run_root, ignore_errors=True)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AppTaskError, OSError, ValueError) as error:
        print(f"benchmark-v9-official: {error}", file=sys.stderr)
        raise SystemExit(1)
