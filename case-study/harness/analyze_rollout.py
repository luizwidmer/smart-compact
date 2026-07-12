#!/usr/bin/env python3
"""Extract comparable token and timing metrics from two Codex rollouts."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path


def timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def parse_rollout(path: str) -> dict[str, object]:
    records = [
        json.loads(line)
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    token_events = [
        record["payload"]["info"]
        for record in records
        if record.get("type") == "event_msg"
        and record.get("payload", {}).get("type") == "token_count"
        and record.get("payload", {}).get("info")
    ]
    if not token_events:
        raise ValueError(f"No token_count events in {path}")

    usage = token_events[-1]["total_token_usage"]
    assistant_messages = 0
    assistant_chars = 0
    tool_calls = 0
    for record in records:
        if record.get("type") != "response_item":
            continue
        payload = record.get("payload", {})
        if payload.get("type") in {"custom_tool_call", "function_call"}:
            tool_calls += 1
        if payload.get("type") != "message" or payload.get("role") != "assistant":
            continue
        assistant_messages += 1
        for part in payload.get("content", []):
            text = part.get("text") if isinstance(part, dict) else None
            if isinstance(text, str):
                assistant_chars += len(text)

    first = timestamp(records[0]["timestamp"])
    last = timestamp(records[-1]["timestamp"])
    input_tokens = usage["input_tokens"]
    cached_input = usage.get("cached_input_tokens", 0)
    return {
        "rollout": path,
        "duration_seconds": round((last - first).total_seconds(), 3),
        "input_tokens": input_tokens,
        "cached_input_tokens": cached_input,
        "uncached_input_tokens": input_tokens - cached_input,
        "output_tokens": usage["output_tokens"],
        "reasoning_output_tokens": usage.get("reasoning_output_tokens", 0),
        "total_tokens": usage["total_tokens"],
        "assistant_messages": assistant_messages,
        "assistant_chars": assistant_chars,
        "tool_calls": tool_calls,
    }


def delta_percent(baseline: int | float, smart_compact: int | float) -> float:
    if not baseline:
        return 0.0
    return round((baseline - smart_compact) / baseline * 100, 1)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--smart-compact", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    baseline = parse_rollout(args.baseline)
    smart_compact = parse_rollout(args.smart_compact)
    comparison = {
        key: delta_percent(baseline[key], smart_compact[key])
        for key in (
            "duration_seconds",
            "input_tokens",
            "cached_input_tokens",
            "uncached_input_tokens",
            "output_tokens",
            "reasoning_output_tokens",
            "total_tokens",
            "assistant_chars",
            "tool_calls",
        )
    }
    print(
        json.dumps(
            {
                "baseline": baseline,
                "smart_compact": smart_compact,
                "savings_pct": comparison,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
