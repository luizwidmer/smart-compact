#!/usr/bin/env python3
"""Run the frozen 15-cell Smart Compact v9 held-out release matrix."""

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
DEFAULT_CASES = ROOT / "benchmarks" / "agentic-v9-heldout.json"
FREEZE = ROOT / "benchmarks" / "v9-freeze.json"
V9_PROFILE = ROOT / "profiles" / "smart-compact-v9.config.toml"
V9_IMPLEMENTATION_PROFILE = (
    ROOT / "profiles" / "smart-compact-v9-implementation.config.toml"
)
V9_NATURAL_PROFILE = ROOT / "profiles" / "smart-compact-v9-natural.config.toml"
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
V9_NATURAL_ARM = "v9-natural-no-spark"
V9_AUTO_ARM = "v9-spark-auto"
PHYSICAL_ARMS = (V6_ARM, V8_ARM, V9_NATURAL_ARM, V9_AUTO_ARM)
VIRTUAL_IMPLEMENTATION_ARM = "v9-selected-implementation"
SEED = 20260715


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


def _cells(
    case_id: str,
    task_shape: str,
    model: str,
    effort: str,
    *,
    natural: bool,
) -> tuple[CellSpec, ...]:
    arms = [V6_ARM, V8_ARM, V9_AUTO_ARM]
    if natural:
        arms.append(V9_NATURAL_ARM)
    return tuple(CellSpec(case_id, task_shape, arm, model, effort) for arm in arms)


MATRIX = (
    *_cells(
        "polyglot-record-normalizer",
        "implementation",
        "gpt-5.6-sol",
        "medium",
        natural=False,
    ),
    *_cells(
        "workspace-permission-migration",
        "migration",
        "gpt-5.6-sol",
        "high",
        natural=True,
    ),
    *_cells(
        "incident-window-correlation",
        "handoff",
        "gpt-5.6-luna",
        "xhigh",
        natural=True,
    ),
    *_cells(
        "ordered-entitlement-ledger",
        "general",
        "gpt-5.6-luna",
        "max",
        natural=True,
    ),
)

IMPLEMENTATION_REUSE_BINDING = {
    "case_id": "polyglot-record-normalizer",
    "source_arm": V6_ARM,
    "bound_arm": VIRTUAL_IMPLEMENTATION_ARM,
    "source_profile": V6_PROFILE.relative_to(ROOT).as_posix(),
    "bound_profile": V9_IMPLEMENTATION_PROFILE.relative_to(ROOT).as_posix(),
    "equivalence": "byte_identical_profile",
    "additional_inference_cells": 0,
}


def matrix_rows(cells: Sequence[CellSpec] = MATRIX) -> list[dict[str, str]]:
    return [{**asdict(cell), "cell_id": cell.cell_id} for cell in cells]


def expected_result_keys(
    cells: Sequence[CellSpec] = MATRIX,
) -> set[tuple[str, str, str, str]]:
    return {(cell.case_id, cell.arm, cell.model, cell.effort) for cell in cells}


def _configured_specs() -> dict[str, benchmark_v8.ArmSpec]:
    return {
        V6_ARM: benchmark_v8.ArmSpec(
            V6_ARM, V6_PROFILE, V6_POLICY, False, False, True, "none"
        ),
        V8_ARM: benchmark_v8.ArmSpec(
            V8_ARM, V8_PROFILE, V8_POLICY, False, False, False, "none"
        ),
        V9_NATURAL_ARM: benchmark_v8.ArmSpec(
            V9_NATURAL_ARM,
            V9_NATURAL_PROFILE,
            None,
            False,
            False,
            False,
            "none",
        ),
        V9_AUTO_ARM: benchmark_v8.ArmSpec(
            V9_AUTO_ARM,
            V9_PROFILE,
            None,
            True,
            True,
            False,
            "auto",
        ),
    }


def build_v9_arm_config(
    original_builder: Any,
    spec: benchmark_v8.ArmSpec,
    profile: dict[str, Any],
) -> dict[str, Any]:
    """Build v9 config without adding a model-visible Spark availability preflight."""
    if spec.name != V9_AUTO_ARM:
        return original_builder(spec, profile)
    config_spec = benchmark_v8.ArmSpec(
        name=spec.name,
        profile_path=spec.profile_path,
        policy_path=spec.policy_path,
        spark_enabled=spec.spark_enabled,
        multi_agent=spec.multi_agent,
        skill_input=spec.skill_input,
        routing_mode="none",
    )
    return original_builder(config_spec, profile)


@contextmanager
def configured_v9_runner() -> Iterator[None]:
    """Install frozen v9 arms into the v8 collector and restore its globals."""
    original_specs = copy.copy(benchmark_v8.ARM_SPECS)
    original_builder = benchmark_v8.build_arm_config

    def builder(spec: benchmark_v8.ArmSpec, profile: dict[str, Any]) -> dict[str, Any]:
        return build_v9_arm_config(original_builder, spec, profile)

    try:
        benchmark_v8.ARM_SPECS.update(_configured_specs())
        benchmark_v8.build_arm_config = builder
        yield
    finally:
        benchmark_v8.ARM_SPECS.clear()
        benchmark_v8.ARM_SPECS.update(original_specs)
        benchmark_v8.build_arm_config = original_builder


def validate_profile_binding() -> dict[str, str]:
    """Prove the reused implementation treatment is exactly the v6 profile bytes."""
    for path in (
        V6_PROFILE,
        V8_PROFILE,
        V9_PROFILE,
        V9_IMPLEMENTATION_PROFILE,
        V9_NATURAL_PROFILE,
    ):
        if not path.is_file():
            raise ValueError(f"required frozen profile not found: {path}")
    v6 = V6_PROFILE.read_bytes()
    implementation = V9_IMPLEMENTATION_PROFILE.read_bytes()
    if implementation != v6:
        raise ValueError(
            "v9 implementation profile must be byte-identical to the v6 control profile"
        )
    return {
        "v6_sha256": hashlib.sha256(v6).hexdigest(),
        "v9_implementation_sha256": hashlib.sha256(implementation).hexdigest(),
        "equivalence": "byte_identical_profile",
    }


def _selected_cases(cases: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    by_id = {case["id"]: case for case in cases}
    expected = {cell.case_id for cell in MATRIX}
    missing = expected - set(by_id)
    extra = set(by_id) - expected
    if missing or extra:
        details = []
        if missing:
            details.append(f"missing={','.join(sorted(missing))}")
        if extra:
            details.append(f"extra={','.join(sorted(extra))}")
        raise ValueError("v9 held-out manifest mismatch: " + " ".join(details))
    return by_id


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
    results: list[dict[str, Any]],
    execution_order: list[dict[str, Any]],
    jobs: int,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "benchmark": "smart-compact-v9-heldout-release",
        "complete": False,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "physical_cells": len(MATRIX),
        "logical_product_cells": len(MATRIX) + 1,
        "repetitions_per_cell": 1,
        "jobs": jobs,
        "execution_order": execution_order,
        "completed_cells": len(results),
        "results": results,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--codex", default=None)
    parser.add_argument("--response-timeout", type=float, default=30.0)
    parser.add_argument("--turn-timeout", type=float, default=900.0)
    parser.add_argument("--drain-timeout", type=float, default=10.0)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--work-root", type=Path, default=None)
    parser.add_argument("--keep-workspaces", action="store_true")
    parser.add_argument("--validate-fixtures", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.jobs < 1:
        raise SystemExit("--jobs must be at least 1")
    if args.drain_timeout < 0:
        raise SystemExit("--drain-timeout cannot be negative")
    cases_path = args.cases.expanduser().resolve()
    cases = benchmark_v8.load_cases(cases_path)
    by_id = _selected_cases(cases)
    fixture_validation = benchmark_v8.validate_v8_fixtures(cases)
    if args.validate_fixtures:
        print(json.dumps(fixture_validation, indent=2, sort_keys=True))
        return 0 if fixture_validation["ok"] else 1
    if not fixture_validation["ok"]:
        raise SystemExit("fixture validation failed")

    binding = validate_profile_binding()
    freeze_sha256 = hashlib.sha256(FREEZE.read_bytes()).hexdigest()
    run_root = args.work_root.expanduser().resolve() if args.work_root else Path(
        tempfile.mkdtemp(prefix="smart-compact-v9-")
    )
    run_root.mkdir(parents=True, exist_ok=True)
    jobs_to_run = list(MATRIX)
    random.Random(args.seed).shuffle(jobs_to_run)
    execution_order = [
        {"index": index, **matrix_rows([cell])[0]}
        for index, cell in enumerate(jobs_to_run)
    ]
    jobs_used = min(args.jobs, len(jobs_to_run))
    results: list[dict[str, Any]] = []
    rank = {cell.cell_id: index for index, cell in enumerate(MATRIX)}

    try:
        with configured_v9_runner():
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
                    if args.output:
                        write_json_payload(
                            args.output,
                            _checkpoint(
                                results=results,
                                execution_order=execution_order,
                                jobs=jobs_used,
                            ),
                        )

            complete = len(results) == len(MATRIX)
            task_gate_passes = sum(task_gate_pass(result) for result in results)
            protocol_misses = [
                result["cell_id"] for result in results if not result.get("protocol_pass")
            ]
            payload = {
                "schema_version": 1,
                "benchmark": "smart-compact-v9-heldout-release",
                "complete": complete,
                "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "cases_path": str(cases_path),
                "cases_sha256": hashlib.sha256(cases_path.read_bytes()).hexdigest(),
                "freeze_path": str(FREEZE),
                "freeze_sha256": freeze_sha256,
                "physical_cells": len(MATRIX),
                "logical_product_cells": len(MATRIX) + 1,
                "repetitions_per_cell": 1,
                "matrix": matrix_rows(),
                "implementation_reuse_binding": {
                    **IMPLEMENTATION_REUSE_BINDING,
                    **binding,
                },
                "treatment": {
                    "v9_auto_availability_prompt_injected": False,
                    "v9_auto_multi_agent_config": True,
                    "forced_spark_included": False,
                    "fixed_worker_cap": None,
                },
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
                "task_gate_passes": task_gate_passes,
                "protocol_misses": protocol_misses,
                "results": results,
            }
            if args.output:
                write_json_payload(args.output, payload)
            print(json.dumps(payload, indent=2, sort_keys=True))
            return 0 if complete and task_gate_passes == len(MATRIX) else 1
    finally:
        if not args.keep_workspaces and args.work_root is None:
            shutil.rmtree(run_root, ignore_errors=True)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AppTaskError, OSError, ValueError, json.JSONDecodeError) as error:
        print(f"benchmark-v9: {error}", file=sys.stderr)
        raise SystemExit(2)
