#!/usr/bin/env python3
"""Check Relay Bench source files against the frozen website contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


REQUIRED_PAGE_STRINGS = (
    'data-testid="site-header"',
    'data-testid="hero"',
    'data-testid="metrics-grid"',
    'data-testid="comparison"',
    'data-testid="methodology"',
    'data-testid="site-footer"',
    'data-window="7"',
    'data-window="30"',
    'data-metric="tokens"',
    'data-metric="saved"',
    'data-metric="parity"',
    'data-metric="runtime"',
    "Same interface. Different context pressure.",
    "Show methodology",
    "Hide methodology",
    "12,480",
    "51,920",
    "31.6%",
    "29.8%",
    "4m 12s",
    "4m 19s",
)

REQUIRED_STYLE_STRINGS = (
    "#F4F1EA",
    "#171A1F",
    "#64615A",
    "#FF5C35",
    "#0B7A75",
    "#D8D2C4",
    "1180px",
    "760px",
    "prefers-reduced-motion",
)

REQUIRED_LAYOUT_STRINGS = (
    "Relay Bench — Context Compression Study",
    "A controlled A/B benchmark for agent context compression.",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("site", help="Site workspace path")
    return parser


def missing(text: str, required: tuple[str, ...]) -> list[str]:
    return [value for value in required if value not in text]


def main() -> int:
    args = build_parser().parse_args()
    root = Path(args.site)
    page = (root / "app/page.tsx").read_text(encoding="utf-8")
    styles = (root / "app/globals.css").read_text(encoding="utf-8")
    layout = (root / "app/layout.tsx").read_text(encoding="utf-8")
    package = json.loads((root / "package.json").read_text(encoding="utf-8"))

    failures = {
        "page": missing(page, REQUIRED_PAGE_STRINGS),
        "styles": missing(styles, REQUIRED_STYLE_STRINGS),
        "layout": missing(layout, REQUIRED_LAYOUT_STRINGS),
    }
    if "SkeletonPreview" in page:
        failures.setdefault("starter", []).append("SkeletonPreview remains in page.tsx")
    if "react-loading-skeleton" in package.get("dependencies", {}):
        failures.setdefault("starter", []).append("react-loading-skeleton remains installed")
    if page.count("<h1") != 1:
        failures.setdefault("semantics", []).append("page.tsx must contain one h1")

    failures = {key: value for key, value in failures.items() if value}
    result = {"ok": not failures, "site": str(root), "failures": failures}
    print(json.dumps(result, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
