#!/usr/bin/env python3
"""Run v8 arms with the isolated natural-language parent contract."""

from __future__ import annotations

import contextlib
import sys
from collections.abc import Iterator, Sequence
from pathlib import Path

if __package__:
    from . import benchmark_v8
else:
    import benchmark_v8


ROOT = Path(__file__).parents[1]
VERBOSE_PROFILE = ROOT / "benchmarks" / "experiments" / "v8-verbose" / "profile.config.toml"
VERBOSE_POLICY = ROOT / "benchmarks" / "experiments" / "v8-verbose" / "SKILL.md"
V8_ARMS = ("v8-no-spark", "v8-spark-forced", "v8-spark-auto")
CONTROL_ARMS = ("standard-no-spark", "v6-no-spark")


def validate_wrapper_args(argv: Sequence[str]) -> tuple[str, ...]:
    """Require an explicit v8-only treatment and forbid profile substitution."""
    arms: list[str] = []
    index = 0
    while index < len(argv):
        value = argv[index]
        if value == "--v8-profile" or value.startswith("--v8-profile="):
            raise ValueError("--v8-profile is forbidden by the verbose experiment")
        if value == "--arm":
            index += 1
            if index >= len(argv) or argv[index].startswith("--"):
                raise ValueError("--arm requires a v8 arm value")
            arms.append(argv[index])
        elif value.startswith("--arm="):
            arms.append(value.split("=", 1)[1])
        index += 1

    if not arms:
        raise ValueError("the verbose experiment requires at least one explicit --arm")
    forbidden = [arm for arm in arms if arm in CONTROL_ARMS]
    if forbidden:
        raise ValueError(f"control arms are forbidden: {', '.join(forbidden)}")
    unknown = [arm for arm in arms if arm not in V8_ARMS]
    if unknown:
        raise ValueError(f"unsupported verbose experiment arms: {', '.join(unknown)}")
    return tuple(arms)


@contextlib.contextmanager
def configured_verbose_arms() -> Iterator[None]:
    """Temporarily rebind only v8 profile and policy paths."""
    if not VERBOSE_PROFILE.is_file() or not VERBOSE_POLICY.is_file():
        raise ValueError("verbose experiment profile and policy must both exist")
    original = {arm: benchmark_v8.ARM_SPECS[arm] for arm in V8_ARMS}
    try:
        for arm, current in original.items():
            benchmark_v8.ARM_SPECS[arm] = benchmark_v8.ArmSpec(
                name=current.name,
                profile_path=VERBOSE_PROFILE,
                policy_path=VERBOSE_POLICY,
                spark_enabled=current.spark_enabled,
                multi_agent=current.multi_agent,
                skill_input=current.skill_input,
                routing_mode=current.routing_mode,
            )
        yield
    finally:
        benchmark_v8.ARM_SPECS.update(original)


def main(argv: Sequence[str] | None = None) -> int:
    selected = list(sys.argv[1:] if argv is None else argv)
    try:
        validate_wrapper_args(selected)
        previous_argv = sys.argv
        with configured_verbose_arms():
            try:
                sys.argv = [previous_argv[0], *selected]
                return benchmark_v8.main()
            finally:
                sys.argv = previous_argv
    except (OSError, ValueError) as error:
        print(f"benchmark-v8-verbose: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
