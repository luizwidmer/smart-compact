#!/usr/bin/env python3
"""Classify compression risk and detect protected-literal omissions."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path


RISK_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "destructive-or-irreversible",
        re.compile(
            r"\b(?:delete|destroy|drop\s+table|truncate|overwrite|revoke|"
            r"force[- ]?push|reset\s+--hard|rm\s+-rf|format\s+(?:disk|drive))\b",
            re.IGNORECASE,
        ),
    ),
    (
        "security-or-permissions",
        re.compile(
            r"\b(?:password|secret|credential|private\s+key|access\s+token|"
            r"authentication|authorization|permission|encryption|chmod\s+777)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "high-stakes",
        re.compile(
            r"\b(?:legal|medical|diagnosis|prescription|investment|tax\s+advice|"
            r"financial\s+advice)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "ordered-procedure",
        re.compile(
            r"(?:^|\n)\s*(?:\d+[.)]|step\s+\d+)\s+|"
            r"(?:^|[.!?]\s+)(?:first|then|finally)\b|"
            r"\b(?:before|after)\s+(?:run|running|change|changing|create|creating|"
            r"delete|deleting|deploy|deploying|execute|executing|apply|applying|"
            r"remove|removing|continue|continuing)\b|"
            r"\bprerequisite\b",
            re.IGNORECASE,
        ),
    ),
    (
        "uncertain-or-ambiguous",
        re.compile(
            r"\b(?:uncertain|unknown|possibly|probably|might|may\s+be|appears|"
            r"inference|cannot\s+confirm)\b",
            re.IGNORECASE,
        ),
    ),
)

PROTECTED_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("fenced-code", re.compile(r"```[\s\S]*?```")),
    ("inline-code", re.compile(r"(?<!`)`[^`\n]+`(?!`)")),
    ("url", re.compile(r"https?://[^\s)>\]}]+")),
    (
        "path",
        re.compile(
            r"(?<![\w.])(?:~?/|\.{1,2}/)[A-Za-z0-9_@%+=:,./-]+"
            r"(?<![.,;:])"
        ),
    ),
    ("environment-variable", re.compile(r"\$[A-Z][A-Z0-9_]*")),
    ("long-flag", re.compile(r"(?<!\w)--[a-zA-Z0-9][a-zA-Z0-9-]*")),
    (
        "number-or-version",
        re.compile(r"(?<![\w.])\d+(?:\.\d+)*(?:%|[A-Za-z]{1,4})?(?![\w.])"),
    ),
)

NEGATIONS = re.compile(
    r"\b(?:not|never|no|without|cannot|can't|won't|don't|doesn't|isn't|mustn't)\b",
    re.IGNORECASE,
)


def read_text(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    return Path(path).read_text(encoding="utf-8")


def classify(text: str) -> dict[str, object]:
    reasons = [name for name, pattern in RISK_PATTERNS if pattern.search(text)]
    return {
        "mode": "full-prose" if reasons else "compact-safe",
        "reasons": reasons,
    }


def protected_literals(text: str) -> dict[str, Counter[str]]:
    found: dict[str, Counter[str]] = {}
    for name, pattern in PROTECTED_PATTERNS:
        values = pattern.findall(text)
        if values:
            found[name] = Counter(values)
    return found


def missing_literals(source: str, candidate: str) -> list[dict[str, object]]:
    source_literals = protected_literals(source)
    candidate_literals = protected_literals(candidate)
    missing: list[dict[str, object]] = []

    for kind, expected in source_literals.items():
        actual = candidate_literals.get(kind, Counter())
        for value, count in expected.items():
            absent = count - actual[value]
            if absent > 0:
                missing.append({"kind": kind, "value": value, "count": absent})

    source_negations = NEGATIONS.findall(source)
    candidate_negations = NEGATIONS.findall(candidate)
    if source_negations and not candidate_negations:
        missing.append(
            {
                "kind": "negation",
                "value": "explicit negative meaning",
                "count": 1,
            }
        )

    return missing


def check(source: str, candidate: str) -> dict[str, object]:
    risk = classify(source)
    missing = missing_literals(source, candidate)
    warnings: list[str] = []
    if risk["mode"] == "full-prose":
        warnings.append("Source contains clarity-gate risk; confirm candidate uses full prose.")

    return {
        "ok": not missing,
        "recommended_mode": risk["mode"],
        "risk_reasons": risk["reasons"],
        "missing": missing,
        "warnings": warnings,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    classify_parser = subparsers.add_parser("classify", help="Classify source risk")
    classify_parser.add_argument("source", help="UTF-8 file path or - for stdin")

    check_parser = subparsers.add_parser(
        "check", help="Check a compact candidate against its source"
    )
    check_parser.add_argument("--source", required=True, help="Source UTF-8 file")
    check_parser.add_argument("--candidate", required=True, help="Candidate UTF-8 file")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "classify":
        result = classify(read_text(args.source))
    else:
        result = check(read_text(args.source), read_text(args.candidate))

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("ok", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
