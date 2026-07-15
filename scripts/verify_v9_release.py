#!/usr/bin/env python3
"""Compatibility verifier for the archived rejected v9 state-minimal run."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_ROOT = (
    ROOT / "benchmarks" / "experiments" / "v9-state-minimal-rejected" / "artifacts"
)
ARCHIVED_VERIFIER = ARCHIVE_ROOT / "scripts" / "verify_v9_release.py"
DEFAULT_FREEZE = ROOT / "benchmarks" / "v9-freeze.json"
DEFAULT_RAW = ROOT / "benchmarks" / "results" / "raw" / "v9-heldout-release.json"
DEFAULT_OUTPUT = ROOT / "benchmarks" / "results" / "v9-release-summary.json"
ARCHIVED_PATHS = {
    "profiles/smart-compact-v9.config.toml": ARCHIVE_ROOT
    / "profiles"
    / "smart-compact-v9.config.toml",
    "versions/v9/SKILL.md": ARCHIVE_ROOT / "versions" / "v9" / "SKILL.md",
    "optimizer/selection.json": ARCHIVE_ROOT / "optimizer" / "selection.json",
    "scripts/verify_v9_release.py": ARCHIVED_VERIFIER,
}


def _load_legacy() -> Any:
    spec = importlib.util.spec_from_file_location(
        "scripts._v9_state_minimal_release_verifier", ARCHIVED_VERIFIER
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load archived v9 verifier")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.ROOT = ROOT
    module.DEFAULT_FREEZE = DEFAULT_FREEZE
    module.DEFAULT_RAW = DEFAULT_RAW
    module.DEFAULT_OUTPUT = DEFAULT_OUTPUT
    return module


_legacy = _load_legacy()
VerificationError = _legacy.VerificationError
_legacy_validate_selector_contract = _legacy.validate_selector_contract


def _artifact_path(relative: str) -> Path:
    return ARCHIVED_PATHS.get(relative, ROOT / relative)


def validate_freeze(path: Path = DEFAULT_FREEZE) -> dict[str, Any]:
    """Validate the rejected freeze against its immutable archived inputs."""
    freeze = _legacy._load_object(path, "v9 freeze")
    _legacy._require(freeze.get("schema_version") == 1, "v9 freeze schema_version must be 1")
    _legacy._require(freeze.get("candidate") == "v9", "v9 freeze candidate mismatch")
    _legacy._require(
        freeze.get("status") == "release_gate_inputs_frozen_before_inference",
        "v9 release inputs are not frozen",
    )
    _legacy._require(freeze.get("primary_objective") == "parent_total_tokens", "objective drift")
    plan = freeze.get("release_plan", {})
    _legacy._require(plan.get("physical_cells") == 15, "must freeze 15 cells")
    _legacy._require(plan.get("repetitions_per_cell") == 1, "v9 release must be one-pass")
    _legacy._require(plan.get("jobs") == 4, "v9 release jobs drift")
    _legacy._require(
        plan.get("wall_time_policy") == "diagnostic_only_contended_parallel_run",
        "wall-time disclosure policy drift",
    )
    _legacy._require(
        plan.get("matrix") == _legacy.benchmark_v9.matrix_rows(),
        "frozen matrix differs from benchmark_v9.MATRIX",
    )
    _legacy._require(
        plan.get("implementation_reuse_binding")
        == _legacy.benchmark_v9.IMPLEMENTATION_REUSE_BINDING,
        "implementation reuse binding drift",
    )
    _legacy._require(
        freeze.get("release_evidence")
        == {
            "status": "outputs_excluded_from_input_freeze",
            "raw_artifacts": [],
            "verified_cells": 0,
        },
        "release outputs must be excluded from the input freeze",
    )
    artifacts = freeze.get("artifacts")
    _legacy._require(isinstance(artifacts, dict) and artifacts, "freeze artifacts are missing")
    for name, artifact in artifacts.items():
        _legacy._require(isinstance(artifact, dict), f"invalid frozen artifact {name}")
        relative = artifact.get("path")
        digest = artifact.get("sha256")
        _legacy._require(isinstance(relative, str) and relative, f"missing path for {name}")
        _legacy._require(
            isinstance(digest, str) and len(digest) == 64,
            f"missing sha256 for {name}",
        )
        target = _artifact_path(relative)
        _legacy._require(target.is_file(), f"frozen artifact missing: {relative}")
        _legacy._require(
            _legacy._sha256(target) == digest,
            f"frozen artifact drift: {relative}",
        )
    v6 = artifacts["v6_profile"]
    implementation = artifacts["v9_implementation_profile"]
    _legacy._require(
        v6["sha256"] == implementation["sha256"],
        "v6 and v9 implementation profile hashes differ",
    )
    _legacy._require(
        _artifact_path(v6["path"]).read_bytes()
        == _artifact_path(implementation["path"]).read_bytes(),
        "v6 and v9 implementation profile bytes differ",
    )
    return freeze


_legacy.validate_freeze = validate_freeze


def validate_selector_contract(freeze: dict[str, Any]) -> list[dict[str, str]]:
    previous_root = _legacy.ROOT
    _legacy.ROOT = ARCHIVE_ROOT
    try:
        return _legacy_validate_selector_contract(freeze)
    finally:
        _legacy.ROOT = previous_root


_legacy.validate_selector_contract = validate_selector_contract


def verify_release(
    raw_path: Path,
    freeze_path: Path = DEFAULT_FREEZE,
) -> dict[str, Any]:
    return _legacy.verify_release(raw_path, freeze_path=freeze_path)


def build_parser() -> Any:
    return _legacy.build_parser()


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = verify_release(
        args.raw.expanduser().resolve(),
        freeze_path=args.freeze.expanduser().resolve(),
    )
    _legacy.write_json_payload(args.output, report)
    print(_legacy.json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except VerificationError as error:
        print(f"verify-v9-release: {error}", file=sys.stderr)
        raise SystemExit(1)
