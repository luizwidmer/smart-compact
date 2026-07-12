#!/usr/bin/env python3
"""Score Smart Compact policy candidates for size, projected calls, and safety."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


DEFAULT_TRACE_CALLS = 23


def projected_calls(text: str, baseline_calls: int = DEFAULT_TRACE_CALLS) -> int:
    lower = text.lower()
    calls = baseline_calls
    if (
        "skip a formal plan" in lower
        or "do not create a plan" in lower
        or "do not create or update a formal plan" in lower
        or "skip plans" in lower
    ):
        calls -= 3
    if "batch independent reads" in lower:
        calls -= 3
    elif "one batched inspection" in lower:
        calls -= 4
    if "inspect only inputs needed" in lower:
        calls -= 1
    if (
        "one consolidated implementation" in lower
        or "complete change in one consolidated patch" in lower
        or "one coherent patch" in lower
    ):
        calls -= 4
    if "one parallel compilation" in lower or "one parallel tool-call group" in lower:
        calls -= 2
    if "one targeted verification command" in lower:
        calls -= 5
    elif "one acceptance suite" in lower:
        calls -= 5
    elif (
        "provided acceptance check once" in lower
        or "one provided acceptance-suite run" in lower
        or "execute the supplied acceptance command verbatim" in lower
    ):
        calls -= 4
    if "one final scope check" in lower or "one scope audit" in lower:
        calls -= 1
    elif (
        "one combined scope/status check" in lower
        or "one final combined status/scope check" in lower
        or "one scoped status check" in lower
    ):
        calls -= 1
    if "target at most eight tool calls" in lower or "target at most eight tool-call groups" in lower:
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


def policy_name(path: Path) -> str:
    if path.name == "SKILL.md":
        return path.parent.name or path.resolve().parent.name
    return path.stem


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("policies", nargs="+", type=Path, help="policy or SKILL.md files to compare")
    parser.add_argument(
        "--baseline-calls",
        type=int,
        default=DEFAULT_TRACE_CALLS,
        help=f"control trace call count (default: {DEFAULT_TRACE_CALLS})",
    )
    parser.add_argument("--encoding", default="o200k_base", help="tiktoken encoding")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.baseline_calls < 1:
        raise SystemExit("--baseline-calls must be positive")
    try:
        import tiktoken
    except ImportError as error:
        raise SystemExit("Install tiktoken in the benchmark environment.") from error

    encoding = tiktoken.get_encoding(args.encoding)
    rows = []
    for path in args.policies:
        text = path.read_text(encoding="utf-8")
        calls = projected_calls(text, args.baseline_calls)
        safety, missing = safety_score(text)
        rows.append(
            {
                "policy": policy_name(path),
                "path": str(path),
                "policy_tokens": len(encoding.encode(text)),
                "projected_trace_calls": calls,
                "projected_call_reduction_pct": round(
                    (args.baseline_calls - calls) / args.baseline_calls * 100,
                    1,
                ),
                "safety_checks": f"{safety}/6",
                "missing_safety_checks": missing,
                "hard_budget": (
                    "target at most eight tool calls" in text.lower()
                    or "target at most eight tool-call groups" in text.lower()
                ),
            }
        )
    print(json.dumps(rows, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
