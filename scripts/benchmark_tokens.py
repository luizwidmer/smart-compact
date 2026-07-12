#!/usr/bin/env python3
"""Measure token savings and guardrail retention for benchmark candidates."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from compact_guard import check, classify


def load_json(path: str) -> object:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", required=True, help="Benchmark cases JSON")
    parser.add_argument("--candidates", required=True, help="Candidate outputs JSON")
    parser.add_argument("--encoding", default="o200k_base", help="tiktoken encoding")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        import tiktoken
    except ImportError as exc:
        raise SystemExit("Install tiktoken in the benchmark environment.") from exc

    cases = load_json(args.cases)
    candidates = load_json(args.candidates)
    if not isinstance(cases, list) or not isinstance(candidates, dict):
        raise SystemExit("Cases must be a list and candidates must be an object.")

    encoding = tiktoken.get_encoding(args.encoding)
    rows: list[dict[str, object]] = []
    totals = defaultdict(int)
    failures = 0

    for case in cases:
        case_id = case["id"]
        source = case["source"]
        candidate = candidates.get(case_id)
        if not isinstance(candidate, str):
            raise SystemExit(f"Missing string candidate for {case_id}")

        source_tokens = len(encoding.encode(source))
        candidate_tokens = len(encoding.encode(candidate))
        saved = source_tokens - candidate_tokens
        savings_pct = (saved / source_tokens * 100) if source_tokens else 0.0
        guard = check(source, candidate)
        actual_mode = classify(source)["mode"]
        mode_ok = actual_mode == case["expected_mode"]
        ok = bool(guard["ok"] and mode_ok)
        failures += int(not ok)

        totals["source"] += source_tokens
        totals["candidate"] += candidate_tokens
        totals[f"source:{case['category']}"] += source_tokens
        totals[f"candidate:{case['category']}"] += candidate_tokens

        rows.append(
            {
                "id": case_id,
                "category": case["category"],
                "expected_mode": case["expected_mode"],
                "actual_mode": actual_mode,
                "mode_ok": mode_ok,
                "guard_ok": guard["ok"],
                "source_tokens": source_tokens,
                "candidate_tokens": candidate_tokens,
                "saved_tokens": saved,
                "savings_pct": round(savings_pct, 1),
                "missing": guard["missing"],
            }
        )

    source_total = totals["source"]
    candidate_total = totals["candidate"]
    summary = {
        "encoding": args.encoding,
        "cases": len(rows),
        "failures": failures,
        "source_tokens": source_total,
        "candidate_tokens": candidate_total,
        "saved_tokens": source_total - candidate_total,
        "savings_pct": round(
            (source_total - candidate_total) / source_total * 100, 1
        ),
    }

    print(json.dumps({"summary": summary, "cases": rows}, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
