#!/usr/bin/env python3
"""Verify optimizer provenance and replay its decision table over recorded cells."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

if __package__:
    from .select_optimizer_profile import load_table, recommend
else:
    from select_optimizer_profile import load_table, recommend


ROOT = Path(__file__).parents[1]


class VerificationError(RuntimeError):
    """Raised when package evidence or replay totals do not match."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    _require(isinstance(value, dict), f"{path} must contain a JSON object")
    return value


def verify(root: Path = ROOT) -> dict[str, Any]:
    table = load_table(root / "optimizer" / "selection.json")
    for source in table["sources"]:
        path = root / source["path"]
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        _require(digest == source["sha256"], f"source hash mismatch: {source['path']}")

    natural = root / "profiles" / "smart-compact-v8-natural.config.toml"
    frozen_natural = root / "benchmarks" / "experiments" / "v8-verbose" / "profile.config.toml"
    _require(natural.read_bytes() == frozen_natural.read_bytes(), "natural profile drifted")

    release = _load_json(root / "benchmarks" / "results" / "v8-release-summary.json")
    verbose = _load_json(root / "benchmarks" / "results" / "v8-verbose-comparison.json")
    _require(release.get("verified") is True, "v8 release summary is not verified")
    _require(verbose.get("verified") is True, "verbose comparison is not verified")

    v6_tokens = {
        (row["scope"], row["model"], row["effort"]): row["v6_parent_tokens"]
        for row in release["parent_token_table"]
    }
    arm_modes = {
        "v8-no-spark": "no_spark",
    }
    selected_total = 0
    terse_total = 0
    cells = 0
    by_mode: dict[str, dict[str, int]] = defaultdict(
        lambda: {"cells": 0, "all_terse_parent_tokens": 0, "selected_parent_tokens": 0}
    )
    lane_cells: dict[str, int] = defaultdict(int)

    for row in verbose["comparisons"]:
        if row["arm"] not in arm_modes:
            continue
        routing_mode = arm_modes[row["arm"]]
        task_shape = table["replay_case_shapes"].get(row["case_id"], "general")
        result = recommend(
            routing_mode,
            task_shape,
            table=table,
        )
        if result["lane"] == "v8-terse":
            selected = row["mechy_parent_tokens"]
        elif result["lane"] == "v8-natural":
            selected = row["verbose_parent_tokens"]
        elif result["lane"] == "v6":
            key = (row["case_id"], row["model"], row["effort"])
            _require(key in v6_tokens, f"missing v6 replay cell: {key}")
            selected = v6_tokens[key]
        else:
            raise VerificationError(f"unknown replay lane: {result['lane']}")

        terse = row["mechy_parent_tokens"]
        cells += 1
        selected_total += selected
        terse_total += terse
        lane_cells[result["lane"]] += 1
        by_mode[routing_mode]["cells"] += 1
        by_mode[routing_mode]["all_terse_parent_tokens"] += terse
        by_mode[routing_mode]["selected_parent_tokens"] += selected

    expected = table["counterfactual_replay"]
    _require(cells == expected["cells"], "replay cell count mismatch")
    _require(terse_total == expected["all_terse_parent_tokens"], "terse replay total mismatch")
    _require(selected_total == expected["selected_parent_tokens"], "selected replay total mismatch")
    _require(dict(by_mode) == expected["by_routing_mode"], "routing replay totals mismatch")
    saved = terse_total - selected_total
    _require(saved == expected["parent_tokens_saved_vs_all_terse"], "replay savings mismatch")
    reduction = round(saved / terse_total * 100, 3)
    _require(
        reduction == expected["parent_token_reduction_pct_vs_all_terse"],
        "replay percentage mismatch",
    )
    return {
        "verified": True,
        "kind": expected["kind"],
        "cells": cells,
        "allTerseParentTokens": terse_total,
        "selectedParentTokens": selected_total,
        "parentTokensSaved": saved,
        "parentTokenReductionPct": reduction,
        "selectedCellsByLane": dict(sorted(lane_cells.items())),
        "byRoutingMode": dict(by_mode),
    }


def main() -> int:
    print(json.dumps(verify(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
