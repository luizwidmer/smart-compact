#!/usr/bin/env python3
"""Freeze the nine-cell recovery for the official workspace-collision non-attempts."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Sequence

if __package__:
    from . import benchmark_v9_official as official
    from . import benchmark_v9_official_recovery as recovery
    from .benchmark_agentic import write_json_payload
else:
    import benchmark_v9_official as official
    import benchmark_v9_official_recovery as recovery
    from benchmark_agentic import write_json_payload


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "benchmarks/v9-official-recovery-freeze.json"
ARTIFACTS = {
    "original_failed_raw": "benchmarks/results/raw/v9-official-release.json",
    "original_freeze": "benchmarks/v9-official-freeze.json",
    "calculator_cases": "benchmarks/agentic-v8-legacy-calculator.json",
    "relay_cases": "benchmarks/agentic-v8-legacy-relay-bench.json",
    "confirmation_cases": "benchmarks/agentic-v8-confirmation.json",
    "v9_local_profile": "profiles/smart-compact-v9.config.toml",
    "v9_spark_profile": "profiles/smart-compact-v9-spark.config.toml",
    "optimizer_selection": "optimizer/selection.json",
    "spark_agent": ".codex/agents/spark-worker.toml",
    "recovery_runner": "scripts/benchmark_v9_official_recovery.py",
    "original_runner": "scripts/benchmark_v9_official.py",
    "final_runner": "scripts/benchmark_v9_final.py",
    "base_runner": "scripts/benchmark_v8.py",
    "grader": "scripts/benchmark_agentic.py",
    "task_client": "scripts/open_app_task.py",
    "recovery_verifier": "scripts/verify_v9_official_recovery.py",
    "original_verifier": "scripts/verify_v9_official.py",
    "dependency_lock": "requirements-benchmark.txt",
    "v8_control_summary": "benchmarks/results/v8-release-summary.json",
}


def blob_id(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def record(relative: str) -> dict[str, str]:
    data = (ROOT / relative).read_bytes()
    return {
        "path": relative,
        "sha256": hashlib.sha256(data).hexdigest(),
        "git_blob": blob_id(data),
    }


def build_freeze() -> dict[str, Any]:
    original = recovery.load_object(recovery.DEFAULT_ORIGINAL)
    full = official.build_matrix(official.load_official_cases())
    cells = recovery.collision_cells(original, full)
    all_ids = {cell.cell_id for cell in full}
    recovery_ids = {cell.cell_id for cell in cells}
    return {
        "schema_version": 1,
        "candidate": "v9-official-collision-recovery",
        "status": "recovery_inputs_frozen_before_inference",
        "primary_objective": "parent_total_tokens",
        "release_plan": {
            "seed": official.SEED,
            "repetitions_per_cell": 1,
            "jobs": 4,
            "physical_cells": 9,
            "case_universe": 3,
            "matrix": official.matrix_rows(cells),
            "execution_order": recovery.execution_order_rows(original, cells),
            "excluded_valid_cell_ids": sorted(all_ids - recovery_ids),
            "recovery_cell_ids": sorted(recovery_ids),
            "wall_time_policy": "diagnostic_only_contended_parallel_run",
        },
        "artifacts": {name: record(path) for name, path in ARTIFACTS.items()},
        "release_evidence": {
            "status": "outputs_excluded_from_input_freeze",
            "raw_artifacts": [],
            "verified_cells": 0,
        },
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    output = args.output.expanduser().resolve()
    if output.exists() and not args.force:
        raise SystemExit(f"refusing to overwrite existing freeze: {output}")
    payload = build_freeze()
    write_json_payload(output, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
