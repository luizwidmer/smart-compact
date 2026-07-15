#!/usr/bin/env python3
"""Build and verify the deployable v9 state-aware hybrid selection."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Sequence

if __package__:
    from . import benchmark_v9_official as official
    from . import benchmark_v9_final as final
    from . import verify_v9_official as controls_verifier
    from . import verify_v9_official_recovery as recovery_verifier
    from .benchmark_agentic import write_json_payload
else:
    import benchmark_v9_official as official
    import benchmark_v9_final as final
    import verify_v9_official as controls_verifier
    import verify_v9_official_recovery as recovery_verifier
    from benchmark_agentic import write_json_payload


ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = ROOT / "benchmarks/results/raw/v9-official-release.json"
RECOVERY = ROOT / "benchmarks/results/raw/v9-official-recovery.json"
CONTROLS = ROOT / "benchmarks/results/v8-release-summary.json"
FRESH = ROOT / "benchmarks/results/raw/v9-final-release.json"
DEFAULT_OUTPUT = ROOT / "benchmarks/results/v9-definitive-summary.json"
EXPECTED_HASHES = {
    ORIGINAL: "690bbb1ac05220068e87fb92501a3f76d2f2d03c33d473bcdd4ed728ee6ca8d3",
    RECOVERY: "338a974e4f8327fb428cc4ad4d542122d4345240b994b4769a72cdb3e094d7aa",
    CONTROLS: "f22d5279bca68749e2794935467db4340e1735c7247d98bf992e8d2c29986430",
    FRESH: "72729e6f2fc2ca9154a6691fc71cadc35905a56218f509c2cd548ada88d1b431",
}


class VerificationError(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"{path}: expected object")
    return value


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pct(saved: int, baseline: int) -> float:
    return round(saved / baseline * 100, 3)


def official_lane(case_id: str, model: str, effort: str) -> str:
    family = "sol" if model.endswith("-sol") else "luna" if model.endswith("-luna") else "other"
    if case_id == "legacy-calculator":
        return "v9-spark" if family == "luna" and effort == "max" else "v9-v8"
    if case_id == "legacy-relay-bench":
        return "v9-v8" if family == "luna" and effort == "max" else "v9"
    if case_id == "monorepo-sdk-migration":
        return "native" if family == "sol" and effort == "medium" else "v9-v8"
    raise VerificationError(f"unsupported official case: {case_id}")


def build_report() -> dict[str, Any]:
    for path, expected in EXPECTED_HASHES.items():
        require(digest(path) == expected, f"frozen source drift: {path}")
    original = load(ORIGINAL)
    recovery = load(RECOVERY)
    controls = load(CONTROLS)
    fresh = load(FRESH)
    cells = official.build_matrix(official.load_official_cases())
    valid, collisions = recovery_verifier.split_original(original, cells)
    recovered = {
        row["cell_id"]: row
        for row in recovery.get("results", [])
        if isinstance(row, dict) and isinstance(row.get("cell_id"), str)
    }
    require(set(recovered) == set(collisions), "recovery result set drift")
    effective = {**valid, **recovered}
    require(len(effective) == 12, "official effective set is not 12 cells")
    require(all(row.get("task_pass") is True for row in effective.values()), "official task failure")
    require(
        all(
            isinstance(row.get("grade"), dict)
            and row["grade"].get("ok") is True
            and row["grade"].get("score_pct") == 100.0
            and row.get("scope_ok") is True
            and row.get("acceptance_observed") is True
            and row.get("usage_complete") is True
            for row in effective.values()
        ),
        "official correctness evidence incomplete",
    )
    controls_index = controls_verifier.control_index(controls)
    official_rows: list[dict[str, Any]] = []
    official_totals = {
        "standard_parent_tokens": 0,
        "v6_parent_tokens": 0,
        "v8_parent_tokens": 0,
        "v9_parent_tokens": 0,
        "v9_child_tokens": 0,
        "v9_spawned_workers": 0,
    }
    for cell in cells:
        control = controls_index[(cell.case_id, cell.model, cell.effort)]
        measured = effective[cell.cell_id]
        lane = official_lane(cell.case_id, cell.model, cell.effort)
        candidates = {
            "native": int(control["standard_parent_tokens"]),
            "v9-v8": int(control["v8_parent_tokens"]),
            "v9": int(measured["parent_total_tokens"]),
            "v9-spark": int(measured["parent_total_tokens"]),
        }
        selected = candidates[lane]
        child = int(measured["child_total_tokens"]) if lane in {"v9", "v9-spark"} else 0
        spawned = int(measured["actual_spawned_workers"]) if lane in {"v9", "v9-spark"} else 0
        if lane != "v9-spark":
            require(spawned == 0, f"{cell.cell_id}: selected non-Spark lane spawned")
        standard = int(control["standard_parent_tokens"])
        v6 = int(control["v6_parent_tokens"])
        v8 = int(control["v8_parent_tokens"])
        official_rows.append(
            {
                "case_id": cell.case_id,
                "task_shape": cell.task_shape,
                "model": cell.model,
                "effort": cell.effort,
                "selected_lane": lane,
                "standard_parent_tokens": standard,
                "v6_parent_tokens": v6,
                "v8_parent_tokens": v8,
                "v9_parent_tokens": selected,
                "v9_saved_vs_standard": standard - selected,
                "v9_saved_vs_v6": v6 - selected,
                "v9_saved_vs_v8": v8 - selected,
                "v9_child_tokens": child,
                "v9_spawned_workers": spawned,
                "task_correct": True,
            }
        )
        official_totals["standard_parent_tokens"] += standard
        official_totals["v6_parent_tokens"] += v6
        official_totals["v8_parent_tokens"] += v8
        official_totals["v9_parent_tokens"] += selected
        official_totals["v9_child_tokens"] += child
        official_totals["v9_spawned_workers"] += spawned
    for version in ("standard", "v6", "v8"):
        baseline = official_totals[f"{version}_parent_tokens"]
        saved = baseline - official_totals["v9_parent_tokens"]
        official_totals[f"v9_saved_vs_{version}"] = saved
        official_totals[f"v9_reduction_pct_vs_{version}"] = pct(saved, baseline)
    require(
        all(
            official_totals["v9_parent_tokens"] < official_totals[f"{version}_parent_tokens"]
            for version in ("standard", "v6", "v8")
        ),
        "definitive v9 does not beat all official whole-version controls",
    )
    uniform_v9_parent_tokens = sum(
        int(row["parent_total_tokens"]) for row in effective.values()
    )
    state_aware_saved = uniform_v9_parent_tokens - official_totals["v9_parent_tokens"]
    require(state_aware_saved > 0, "state-aware routing does not beat uniform v9 state")
    uniform_state_candidate = {
        "status": "rejected",
        "parent_tokens": uniform_v9_parent_tokens,
        "state_aware_parent_tokens": official_totals["v9_parent_tokens"],
        "state_aware_saved_tokens": state_aware_saved,
        "state_aware_reduction_pct": pct(state_aware_saved, uniform_v9_parent_tokens),
    }

    fresh_rows_by_shape_arm = {
        (row["task_shape"], row["arm"]): row for row in fresh.get("results", [])
    }
    fresh_selection = {
        "implementation": final.V8_ARM,
        "migration": final.V8_ARM,
        "handoff": final.V9_SELECTED_LOCAL_ARM,
        "general": final.V9_SELECTED_LOCAL_ARM,
    }
    fresh_rows: list[dict[str, Any]] = []
    fresh_totals = {"v6_parent_tokens": 0, "v8_parent_tokens": 0, "v9_parent_tokens": 0}
    for shape in final.TASK_SHAPES:
        selected_arm = fresh_selection[shape]
        selected = fresh_rows_by_shape_arm[(shape, selected_arm)]
        v6 = fresh_rows_by_shape_arm[(shape, final.V6_ARM)]
        v8 = fresh_rows_by_shape_arm[(shape, final.V8_ARM)]
        require(selected.get("task_pass") is True, f"fresh {shape} selection failed")
        fresh_rows.append(
            {
                "task_shape": shape,
                "model": selected["model"],
                "effort": selected["effort"],
                "selected_lane": "v9-v8" if selected_arm == final.V8_ARM else "v9",
                "v6_parent_tokens": int(v6["parent_total_tokens"]),
                "v8_parent_tokens": int(v8["parent_total_tokens"]),
                "v9_parent_tokens": int(selected["parent_total_tokens"]),
                "task_correct": True,
            }
        )
        fresh_totals["v6_parent_tokens"] += int(v6["parent_total_tokens"])
        fresh_totals["v8_parent_tokens"] += int(v8["parent_total_tokens"])
        fresh_totals["v9_parent_tokens"] += int(selected["parent_total_tokens"])
    for version in ("v6", "v8"):
        baseline = fresh_totals[f"{version}_parent_tokens"]
        saved = baseline - fresh_totals["v9_parent_tokens"]
        fresh_totals[f"v9_saved_vs_{version}"] = saved
        fresh_totals[f"v9_reduction_pct_vs_{version}"] = pct(saved, baseline)
    require(
        fresh_totals["v9_parent_tokens"] < fresh_totals["v6_parent_tokens"]
        and fresh_totals["v9_parent_tokens"] < fresh_totals["v8_parent_tokens"],
        "definitive v9 does not beat both fresh controls",
    )
    combined = {
        "v6_parent_tokens": official_totals["v6_parent_tokens"] + fresh_totals["v6_parent_tokens"],
        "v8_parent_tokens": official_totals["v8_parent_tokens"] + fresh_totals["v8_parent_tokens"],
        "v9_parent_tokens": official_totals["v9_parent_tokens"] + fresh_totals["v9_parent_tokens"],
    }
    for version in ("v6", "v8"):
        baseline = combined[f"{version}_parent_tokens"]
        saved = baseline - combined["v9_parent_tokens"]
        combined[f"v9_saved_vs_{version}"] = saved
        combined[f"v9_reduction_pct_vs_{version}"] = pct(saved, baseline)
    return {
        "schema_version": 1,
        "status": "v9_definitive_selection_verified",
        "evidence_status": "post_matrix_deployable_hybrid_selection_not_blinded_confirmation",
        "primary_objective": "parent_total_tokens",
        "state_cost_finding": "one instruction state did not dominate; v9 routes among native, v8-derived, minimal-local, and Spark treatments",
        "uniform_state_candidate": uniform_state_candidate,
        "v6_positive_points": "folded into the minimal v9 workflow; direct v6 benchmark rows are controls because their skill-input treatment is not profile-only",
        "official": {"rows": official_rows, "totals": official_totals},
        "fresh_additions": {"rows": fresh_rows, "totals": fresh_totals},
        "combined": combined,
        "selected_official_spawned_workers": official_totals["v9_spawned_workers"],
        "selected_official_parent_tokens_saved_per_spawned_worker_vs_v8": round(
            official_totals["v9_saved_vs_v8"] / official_totals["v9_spawned_workers"], 3
        ),
        "task_correct_cells": 16,
        "protocol_only_misses_nonblocking": sorted(
            row["cell_id"] for row in effective.values() if row.get("protocol_pass") is not True
        ),
        "rtk_only_misses_nonblocking": sorted(
            row["cell_id"]
            for row in effective.values()
            if row.get("task_pass") is True and row.get("rtk_ok") is not True
        ),
        "source_hashes": {str(path.relative_to(ROOT)): expected for path, expected in EXPECTED_HASHES.items()},
        "limitations": [
            "one observation per cell",
            "route selection follows observed matrices and is not blinded confirmation",
            "wall time is nonpublishable because runs were parallel and contended",
        ],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    report = build_report()
    write_json_payload(args.output.expanduser().resolve(), report)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except VerificationError as error:
        print(f"verify-v9-definitive: {error}", file=sys.stderr)
        raise SystemExit(1)
