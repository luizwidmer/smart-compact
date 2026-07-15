#!/usr/bin/env python3
"""Run the one-pass 14-cell Smart Compact v9 final release matrix."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import random
import shutil
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterator, Sequence

if __package__:
    from . import benchmark_v8
    from .benchmark_agentic import command_version, write_json_payload
    from .open_app_task import AppTaskError, resolve_codex
else:
    import benchmark_v8
    from benchmark_agentic import command_version, write_json_payload
    from open_app_task import AppTaskError, resolve_codex


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASES = ROOT / "benchmarks" / "agentic-v9-final.json"
DEFAULT_FREEZE = ROOT / "benchmarks" / "v9-final-freeze.json"
DEFAULT_OUTPUT = ROOT / "benchmarks" / "results" / "raw" / "v9-final-release.json"
V9_LOCAL_PROFILE = ROOT / "profiles" / "smart-compact-v9.config.toml"
V9_SPARK_PROFILE = ROOT / "profiles" / "smart-compact-v9-spark.config.toml"
V6_PROFILE = ROOT / "benchmarks" / "profiles" / "v6.config.toml"
V6_POLICY = ROOT / "benchmarks" / "policies" / "v6" / "SKILL.md"
V8_PROFILE = (
    ROOT
    / "benchmarks"
    / "retired"
    / "package"
    / "profiles"
    / "smart-compact-v8.config.toml"
)
V8_POLICY = ROOT / "benchmarks" / "policies" / "v8" / "SKILL.md"

V6_ARM = "v6-no-spark"
V8_ARM = "v8-no-spark"
V9_SELECTED_SPARK_ARM = "v9-selected-spark"
V9_SELECTED_LOCAL_ARM = "v9-selected-local"
V9_LOCAL_COUNTERFACTUAL_ARM = "v9-local-counterfactual"
PHYSICAL_ARMS = (
    V6_ARM,
    V8_ARM,
    V9_SELECTED_SPARK_ARM,
    V9_SELECTED_LOCAL_ARM,
    V9_LOCAL_COUNTERFACTUAL_ARM,
)
TASK_SHAPES = ("implementation", "migration", "handoff", "general")
SPARK_SHAPES = frozenset(("implementation", "migration"))
LOCAL_SHAPES = frozenset(("handoff", "general"))
SETTINGS = {
    "implementation": ("gpt-5.6-sol", "medium"),
    "migration": ("gpt-5.6-sol", "high"),
    "handoff": ("gpt-5.6-luna", "xhigh"),
    "general": ("gpt-5.6-luna", "max"),
}
SEED = 20260715
FINAL_TREATMENT = {
    "availability_prompt_injected": False,
    "selected_spark_multi_agent_config": True,
    "selected_local_multi_agent_config": False,
    "fixed_worker_cap": None,
    "spark_shapes": sorted(SPARK_SHAPES),
    "local_shapes": sorted(LOCAL_SHAPES),
    "local_counterfactual_shapes": sorted(SPARK_SHAPES),
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
        return f"{self.case_id}::{self.arm}"


def _case_ids_by_shape(cases: Sequence[dict[str, Any]]) -> dict[str, str]:
    by_shape: dict[str, str] = {}
    for case in cases:
        case_id = case.get("id")
        shape = case.get("category")
        if not isinstance(case_id, str) or not case_id:
            raise ValueError("every final case must have a non-empty id")
        if shape not in TASK_SHAPES:
            raise ValueError(f"{case_id}: unsupported final category {shape!r}")
        if shape in by_shape:
            raise ValueError(f"final manifest has multiple {shape} cases")
        by_shape[shape] = case_id
    if set(by_shape) != set(TASK_SHAPES):
        missing = sorted(set(TASK_SHAPES) - set(by_shape))
        raise ValueError(f"final manifest must contain one case per task shape; missing={missing}")
    if len(cases) != len(TASK_SHAPES):
        raise ValueError("final manifest must contain exactly four cases")
    return by_shape


def build_matrix(cases: Sequence[dict[str, Any]]) -> tuple[CellSpec, ...]:
    """Build four controls, four selected cells, and two local counterfactuals."""
    case_ids = _case_ids_by_shape(cases)
    cells: list[CellSpec] = []
    for shape in TASK_SHAPES:
        model, effort = SETTINGS[shape]
        case_id = case_ids[shape]
        arms = [V6_ARM, V8_ARM]
        if shape in SPARK_SHAPES:
            arms.extend((V9_SELECTED_SPARK_ARM, V9_LOCAL_COUNTERFACTUAL_ARM))
        else:
            arms.append(V9_SELECTED_LOCAL_ARM)
        cells.extend(CellSpec(case_id, shape, arm, model, effort) for arm in arms)
    return tuple(cells)


def matrix_rows(cells: Sequence[CellSpec]) -> list[dict[str, str]]:
    return [{**asdict(cell), "cell_id": cell.cell_id} for cell in cells]


def execution_order_rows(
    cells: Sequence[CellSpec],
    seed: int = SEED,
) -> list[dict[str, Any]]:
    shuffled = list(cells)
    random.Random(seed).shuffle(shuffled)
    return [
        {"index": index, **matrix_rows([cell])[0]}
        for index, cell in enumerate(shuffled)
    ]


def validate_matrix_rows(rows: object) -> tuple[CellSpec, ...]:
    """Validate the self-describing matrix without depending on a future freeze."""
    if not isinstance(rows, list) or len(rows) != 14:
        raise ValueError("final matrix must contain exactly 14 cells")
    cells: list[CellSpec] = []
    expected_keys = {"case_id", "task_shape", "arm", "model", "effort", "cell_id"}
    for row in rows:
        if not isinstance(row, dict) or set(row) != expected_keys:
            raise ValueError("invalid final matrix row")
        values = [row.get(key) for key in ("case_id", "task_shape", "arm", "model", "effort")]
        if not all(isinstance(value, str) and value for value in values):
            raise ValueError("final matrix row fields must be non-empty strings")
        cell = CellSpec(*values)
        if row.get("cell_id") != cell.cell_id:
            raise ValueError(f"{cell.cell_id}: matrix cell_id mismatch")
        cells.append(cell)
    if len({cell.cell_id for cell in cells}) != len(cells):
        raise ValueError("final matrix cell IDs must be unique")
    case_ids: dict[str, set[str]] = {shape: set() for shape in TASK_SHAPES}
    for cell in cells:
        if cell.task_shape not in SETTINGS:
            raise ValueError(f"unsupported task shape {cell.task_shape}")
        if (cell.model, cell.effort) != SETTINGS[cell.task_shape]:
            raise ValueError(f"{cell.cell_id}: model/effort drift")
        case_ids[cell.task_shape].add(cell.case_id)
    if any(len(ids) != 1 for ids in case_ids.values()):
        raise ValueError("final matrix must bind exactly one case to each task shape")
    for shape, ids in case_ids.items():
        case_id = next(iter(ids))
        observed = {cell.arm for cell in cells if cell.case_id == case_id}
        expected = {V6_ARM, V8_ARM}
        if shape in SPARK_SHAPES:
            expected.update((V9_SELECTED_SPARK_ARM, V9_LOCAL_COUNTERFACTUAL_ARM))
        else:
            expected.add(V9_SELECTED_LOCAL_ARM)
        if observed != expected:
            raise ValueError(f"{shape}: final arm allocation drift")
    return tuple(cells)


def validate_release_freeze(
    path: Path,
    cases_path: Path,
    matrix: Sequence[CellSpec],
) -> dict[str, Any]:
    """Reject any final inference input that differs from the pre-run freeze."""
    freeze = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(freeze, dict):
        raise ValueError("final freeze must be a JSON object")
    if freeze.get("schema_version") != 1 or freeze.get("candidate") != "v9-definitive":
        raise ValueError("final freeze identity drift")
    if freeze.get("status") != "release_gate_inputs_frozen_before_inference":
        raise ValueError("final inputs were not frozen before inference")
    if freeze.get("primary_objective") != "parent_total_tokens":
        raise ValueError("final freeze objective drift")
    if freeze.get("treatment") != FINAL_TREATMENT:
        raise ValueError("final freeze treatment drift")
    plan = freeze.get("release_plan")
    if not isinstance(plan, dict):
        raise ValueError("final freeze release plan missing")
    expected_plan = {
        "seed": SEED,
        "repetitions_per_cell": 1,
        "jobs": 4,
        "physical_cells": 14,
        "case_universe": 4,
        "matrix": matrix_rows(matrix),
        "execution_order": execution_order_rows(matrix),
        "release_cell_allocation": {
            V6_ARM: 4,
            V8_ARM: 4,
            V9_SELECTED_SPARK_ARM: 2,
            V9_SELECTED_LOCAL_ARM: 2,
            V9_LOCAL_COUNTERFACTUAL_ARM: 2,
        },
        "wall_time_policy": "diagnostic_only_contended_parallel_run",
    }
    if plan != expected_plan:
        raise ValueError("final freeze release plan drift")
    if freeze.get("release_evidence") != {
        "status": "outputs_excluded_from_input_freeze",
        "raw_artifacts": [],
        "verified_cells": 0,
    }:
        raise ValueError("final freeze must exclude release outputs")
    artifacts = freeze.get("artifacts")
    if not isinstance(artifacts, dict) or not artifacts:
        raise ValueError("final freeze artifacts missing")
    for name, artifact in artifacts.items():
        if not isinstance(artifact, dict):
            raise ValueError(f"invalid final frozen artifact {name}")
        relative = artifact.get("path")
        digest = artifact.get("sha256")
        if not isinstance(relative, str) or not isinstance(digest, str):
            raise ValueError(f"incomplete final frozen artifact {name}")
        target = (ROOT / relative).resolve()
        try:
            target.relative_to(ROOT)
        except ValueError as error:
            raise ValueError(f"final frozen artifact escapes repository: {relative}") from error
        if not target.is_file() or hashlib.sha256(target.read_bytes()).hexdigest() != digest:
            raise ValueError(f"final frozen artifact drift: {relative}")
    cases = artifacts.get("final_cases")
    try:
        cases_relative = str(cases_path.resolve().relative_to(ROOT))
    except ValueError as error:
        raise ValueError("final cases must be inside the repository") from error
    if not isinstance(cases, dict) or cases.get("path") != cases_relative:
        raise ValueError("final cases are not bound by the freeze")
    return freeze


def _configured_specs() -> dict[str, benchmark_v8.ArmSpec]:
    return {
        V6_ARM: benchmark_v8.ArmSpec(
            V6_ARM, V6_PROFILE, V6_POLICY, False, False, True, "none"
        ),
        V8_ARM: benchmark_v8.ArmSpec(
            V8_ARM, V8_PROFILE, V8_POLICY, False, False, False, "none"
        ),
        V9_SELECTED_SPARK_ARM: benchmark_v8.ArmSpec(
            V9_SELECTED_SPARK_ARM,
            V9_SPARK_PROFILE,
            None,
            True,
            True,
            False,
            "auto",
        ),
        V9_SELECTED_LOCAL_ARM: benchmark_v8.ArmSpec(
            V9_SELECTED_LOCAL_ARM,
            V9_LOCAL_PROFILE,
            None,
            False,
            False,
            False,
            "none",
        ),
        V9_LOCAL_COUNTERFACTUAL_ARM: benchmark_v8.ArmSpec(
            V9_LOCAL_COUNTERFACTUAL_ARM,
            V9_LOCAL_PROFILE,
            None,
            False,
            False,
            False,
            "none",
        ),
    }


def build_final_arm_config(
    original_builder: Any,
    spec: benchmark_v8.ArmSpec,
    profile: dict[str, Any],
) -> dict[str, Any]:
    """Build the Spark lane without the historical availability prompt."""
    if spec.name != V9_SELECTED_SPARK_ARM:
        return original_builder(spec, profile)
    prompt_free_spec = benchmark_v8.ArmSpec(
        name=spec.name,
        profile_path=spec.profile_path,
        policy_path=spec.policy_path,
        spark_enabled=spec.spark_enabled,
        multi_agent=spec.multi_agent,
        skill_input=spec.skill_input,
        routing_mode="none",
    )
    return original_builder(prompt_free_spec, profile)


@contextmanager
def configured_final_runner() -> Iterator[None]:
    original_specs = copy.copy(benchmark_v8.ARM_SPECS)
    original_builder = benchmark_v8.build_arm_config

    def builder(spec: benchmark_v8.ArmSpec, profile: dict[str, Any]) -> dict[str, Any]:
        return build_final_arm_config(original_builder, spec, profile)

    try:
        benchmark_v8.ARM_SPECS.update(_configured_specs())
        benchmark_v8.build_arm_config = builder
        yield
    finally:
        benchmark_v8.ARM_SPECS.clear()
        benchmark_v8.ARM_SPECS.update(original_specs)
        benchmark_v8.build_arm_config = original_builder


def task_gate_pass(result: dict[str, Any]) -> bool:
    grade = result.get("grade")
    return bool(
        result.get("task_pass")
        and isinstance(grade, dict)
        and grade.get("ok")
        and grade.get("score_pct") == 100.0
        and result.get("scope_ok")
        and result.get("acceptance_observed")
        and result.get("usage_complete")
        and result.get("rtk_ok")
        and result.get("no_active_children")
        and isinstance(result.get("parent_total_tokens"), int)
        and not isinstance(result.get("parent_total_tokens"), bool)
        and result["parent_total_tokens"] > 0
    )


def _run_cell(
    *,
    cell: CellSpec,
    case: dict[str, Any],
    order_index: int,
    run_root: Path,
    codex: str,
    profile: dict[str, Any],
    response_timeout: float,
    turn_timeout: float,
    drain_timeout: float,
    keep_workspaces: bool,
) -> dict[str, Any]:
    result = benchmark_v8.execute_arm_job(
        case=case,
        arm=cell.arm,
        trial=1,
        order_index=order_index,
        run_root=run_root,
        codex=codex,
        profile=profile,
        model=cell.model,
        effort=cell.effort,
        response_timeout=response_timeout,
        turn_timeout=turn_timeout,
        drain_timeout=drain_timeout,
        keep_workspaces=keep_workspaces,
    )
    result.update(
        {
            "cell_id": cell.cell_id,
            "task_shape": cell.task_shape,
            "model": cell.model,
            "effort": cell.effort,
        }
    )
    result["task_gate_pass"] = task_gate_pass(result)
    return result


def _checkpoint(
    *,
    matrix: Sequence[CellSpec],
    results: list[dict[str, Any]],
    execution_order: list[dict[str, Any]],
    jobs: int,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "benchmark": "smart-compact-v9-final-release",
        "complete": False,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "physical_cells": len(matrix),
        "repetitions_per_cell": 1,
        "jobs": jobs,
        "matrix": matrix_rows(matrix),
        "execution_order": execution_order,
        "completed_cells": len(results),
        "results": results,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
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
        raise SystemExit("the frozen final release requires --jobs 4")
    if not args.validate_fixtures and args.seed != SEED:
        raise SystemExit(f"the frozen final release requires --seed {SEED}")
    if args.drain_timeout < 0:
        raise SystemExit("--drain-timeout cannot be negative")
    cases_path = args.cases.expanduser().resolve()
    cases = benchmark_v8.load_cases(cases_path)
    matrix = build_matrix(cases)
    fixture_validation = benchmark_v8.validate_v8_fixtures(cases)
    if args.validate_fixtures:
        print(json.dumps(fixture_validation, indent=2, sort_keys=True))
        return 0 if fixture_validation["ok"] else 1
    if not fixture_validation["ok"]:
        raise SystemExit("fixture validation failed")
    freeze_path = args.freeze.expanduser().resolve()
    validate_release_freeze(freeze_path, cases_path, matrix)

    by_id = {case["id"]: case for case in cases}
    run_root = args.work_root.expanduser().resolve() if args.work_root else Path(
        tempfile.mkdtemp(prefix="smart-compact-v9-final-")
    )
    run_root.mkdir(parents=True, exist_ok=True)
    execution_order = execution_order_rows(matrix, args.seed)
    by_cell_id = {cell.cell_id: cell for cell in matrix}
    jobs_to_run = [by_cell_id[row["cell_id"]] for row in execution_order]
    jobs_used = min(args.jobs, len(jobs_to_run))
    results: list[dict[str, Any]] = []
    rank = {cell.cell_id: index for index, cell in enumerate(matrix)}

    try:
        with configured_final_runner():
            profiles = benchmark_v8.load_arm_profiles(list(PHYSICAL_ARMS))
            codex = resolve_codex(args.codex)
            spark_agent = benchmark_v8.validate_v8_spark_agent(
                codex, args.response_timeout, "gpt-5.6-luna"
            )
            with ThreadPoolExecutor(max_workers=jobs_used) as executor:
                futures = {
                    executor.submit(
                        _run_cell,
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
                    results.append(result)
                    results.sort(key=lambda row: rank[row["cell_id"]])
                    write_json_payload(
                        args.output,
                        _checkpoint(
                            matrix=matrix,
                            results=results,
                            execution_order=execution_order,
                            jobs=jobs_used,
                        ),
                    )

            payload = {
                "schema_version": 1,
                "benchmark": "smart-compact-v9-final-release",
                "complete": len(results) == len(matrix),
                "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "cases_path": str(cases_path),
                "cases_sha256": hashlib.sha256(cases_path.read_bytes()).hexdigest(),
                "freeze_path": str(freeze_path),
                "freeze_sha256": hashlib.sha256(freeze_path.read_bytes()).hexdigest(),
                "physical_cells": len(matrix),
                "repetitions_per_cell": 1,
                "matrix": matrix_rows(matrix),
                "treatment": FINAL_TREATMENT,
                "arm_metadata": benchmark_v8.arm_metadata(list(PHYSICAL_ARMS)),
                "disabled_skill_path": str(benchmark_v8.INSTALLED_SKILL),
                "spark_agent": spark_agent,
                "codex": codex,
                "codex_version": command_version([codex, "--version"]),
                "rtk_version": command_version(["rtk", "--version"]),
                "seed": args.seed,
                "jobs": jobs_used,
                "wall_time_contended": jobs_used > 1,
                "execution_order": execution_order,
                "fixture_validation": fixture_validation,
                "task_gate_passes": sum(task_gate_pass(row) for row in results),
                "runner_status": "matrix_complete_not_release_verdict",
                "protocol_misses": sorted(
                    row["cell_id"] for row in results if row.get("protocol_pass") is not True
                ),
                "results": results,
            }
            write_json_payload(args.output, payload)
            print(json.dumps(payload, indent=2, sort_keys=True))
            return 0 if payload["complete"] and payload["task_gate_passes"] == 14 else 1
    finally:
        if not args.keep_workspaces and args.work_root is None:
            shutil.rmtree(run_root, ignore_errors=True)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AppTaskError, OSError, ValueError) as error:
        print(f"benchmark-v9-final: {error}", file=sys.stderr)
        raise SystemExit(1)
