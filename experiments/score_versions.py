#!/usr/bin/env python3
"""Score Compact policy candidates against the accepted calculator trace."""

from __future__ import annotations

import json
from pathlib import Path

import tiktoken


ROOT = Path(__file__).resolve().parents[1]
CURRENT_TRACE_CALLS = 23


def projected_calls(text: str) -> int:
    lower = text.lower()
    calls = CURRENT_TRACE_CALLS
    if "skip a formal plan" in lower or "do not create a plan" in lower:
        calls -= 3
    if "batch independent reads" in lower:
        calls -= 3
    elif "one batched inspection" in lower:
        calls -= 4
    if "inspect only inputs needed" in lower:
        calls -= 1
    if "one targeted verification command" in lower:
        calls -= 5
    elif "one acceptance suite" in lower:
        calls -= 5
    if "one final scope check" in lower or "one scope audit" in lower:
        calls -= 1
    if "target at most eight tool calls" in lower:
        calls = min(calls, 8)
    return max(calls, 1)


def safety_score(text: str) -> tuple[int, list[str]]:
    lower = text.lower()
    checks = {
        "exact literals": "preserve" in lower and "numbers" in lower and "negation" in lower,
        "security escape": "security" in lower,
        "destructive escape": "destructive" in lower,
        "ambiguity escape": "ambiguous" in lower,
        "verification escape": "verification" in lower or "acceptance" in lower,
        "failure escape": "fail" in lower or "evidence" in lower,
    }
    missing = [name for name, ok in checks.items() if not ok]
    return len(checks) - len(missing), missing


def main() -> None:
    encoding = tiktoken.get_encoding("o200k_base")
    candidates = {
        "v0-original": ROOT / "experiments/versions/v0-original/SKILL.md",
        "v1-minimal": ROOT / "experiments/versions/v1-minimal/SKILL.md",
        "v2-adaptive": ROOT / "experiments/versions/v2-adaptive/SKILL.md",
        "v3-hard-budget": ROOT / "experiments/versions/v3-hard-budget/SKILL.md",
        "promoted": ROOT / "SKILL.md",
    }
    rows = []
    for name, path in candidates.items():
        text = path.read_text()
        calls = projected_calls(text)
        safety, missing = safety_score(text)
        rows.append(
            {
                "version": name,
                "policy_tokens": len(encoding.encode(text)),
                "projected_trace_calls": calls,
                "projected_call_reduction_pct": round(
                    (CURRENT_TRACE_CALLS - calls) / CURRENT_TRACE_CALLS * 100, 1
                ),
                "safety_checks": f"{safety}/6",
                "missing_safety_checks": missing,
                "hard_budget": "target at most eight tool calls" in text.lower(),
            }
        )
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
