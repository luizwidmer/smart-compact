#!/usr/bin/env python3
"""Run the final one-cell Spark routing probe on the implementation shape."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__:
    from . import benchmark_v8
else:
    import benchmark_v8


ROOT = Path(__file__).parents[1]
PROBE_ARM = "v9-routing-probe-r3"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--profile",
        type=Path,
        default=ROOT / "benchmarks" / "experiments" / "v9-routing-probe-r3" / "profile.config.toml",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "benchmarks" / "results" / "raw" / "v9-routing-probe-r3.json",
    )
    parser.add_argument("--codex", default=None)
    return parser


def configure_probe(profile: Path) -> benchmark_v8.ArmSpec:
    spec = benchmark_v8.ArmSpec(
        PROBE_ARM,
        profile,
        None,
        True,
        True,
        False,
        "none",
    )
    benchmark_v8.ARM_SPECS[PROBE_ARM] = spec
    return spec


def main() -> int:
    args = build_parser().parse_args()
    profile = args.profile.expanduser().resolve()
    if not profile.is_file():
        raise SystemExit(f"profile not found: {profile}")
    configure_probe(profile)
    delegated_argv = [
        str(Path(sys.argv[0])),
        "--cases",
        str(ROOT / "benchmarks" / "agentic-v9-heldout.json"),
        "--case",
        "polyglot-record-normalizer",
        "--arm",
        PROBE_ARM,
        "--jobs",
        "1",
        "--model",
        "gpt-5.6-sol",
        "--effort",
        "medium",
        "--output",
        str(args.output),
    ]
    if args.codex:
        delegated_argv.extend(("--codex", args.codex))
    sys.argv = delegated_argv
    return benchmark_v8.main()


if __name__ == "__main__":
    raise SystemExit(main())
