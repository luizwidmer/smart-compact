#!/usr/bin/env python3
"""Freeze every input to the v9 official-completion inference run."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Sequence

if __package__:
    from . import benchmark_v9_official as benchmark
    from .benchmark_agentic import write_json_payload
else:
    import benchmark_v9_official as benchmark
    from benchmark_agentic import write_json_payload


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "benchmarks" / "v9-official-freeze.json"
ARTIFACTS = {
    "calculator_cases": "benchmarks/agentic-v8-legacy-calculator.json",
    "relay_cases": "benchmarks/agentic-v8-legacy-relay-bench.json",
    "confirmation_cases": "benchmarks/agentic-v8-confirmation.json",
    "v9_local_profile": "profiles/smart-compact-v9.config.toml",
    "v9_spark_profile": "profiles/smart-compact-v9-spark.config.toml",
    "optimizer_selection": "optimizer/selection.json",
    "spark_agent": ".codex/agents/spark-worker.toml",
    "runner": "scripts/benchmark_v9_official.py",
    "final_runner": "scripts/benchmark_v9_final.py",
    "base_runner": "scripts/benchmark_v8.py",
    "grader": "scripts/benchmark_agentic.py",
    "task_client": "scripts/open_app_task.py",
    "release_verifier": "scripts/verify_v9_official.py",
    "dependency_lock": "requirements-benchmark.txt",
    "v8_control_summary": "benchmarks/results/v8-release-summary.json",
    "v9_selection_summary": "benchmarks/results/v9-selection-summary.json",
}


def git_blob_id(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("utf-8")
    return hashlib.sha1(header + data).hexdigest()


def artifact_record(relative: str) -> dict[str, str]:
    data = (ROOT / relative).read_bytes()
    return {
        "path": relative,
        "sha256": hashlib.sha256(data).hexdigest(),
        "git_blob": git_blob_id(data),
    }


def build_freeze() -> dict[str, Any]:
    matrix = benchmark.build_matrix(benchmark.load_official_cases())
    return {
        "schema_version": 1,
        "candidate": "v9-official-completion",
        "status": "official_inputs_frozen_before_inference",
        "primary_objective": "parent_total_tokens",
        "treatment": benchmark.OFFICIAL_TREATMENT,
        "release_plan": {
            "seed": benchmark.SEED,
            "repetitions_per_cell": 1,
            "jobs": 4,
            "physical_cells": 12,
            "case_universe": 3,
            "matrix": benchmark.matrix_rows(matrix),
            "execution_order": benchmark.execution_order_rows(matrix),
            "release_cell_allocation": {
                benchmark.final.V9_SELECTED_SPARK_ARM: 4,
                benchmark.final.V9_SELECTED_LOCAL_ARM: 8,
            },
            "settings": [list(setting) for setting in benchmark.SETTINGS],
            "wall_time_policy": "diagnostic_only_contended_parallel_run",
        },
        "artifacts": {
            name: artifact_record(relative) for name, relative in ARTIFACTS.items()
        },
        "release_evidence": {
            "status": "outputs_excluded_from_input_freeze",
            "raw_artifacts": [],
            "verified_cells": 0,
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--force", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output = args.output.expanduser().resolve()
    if output.exists() and not args.force:
        raise SystemExit(f"refusing to overwrite existing freeze: {output}")
    payload = build_freeze()
    write_json_payload(output, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
