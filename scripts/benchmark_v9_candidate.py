#!/usr/bin/env python3
"""Run v8 evaluator arms with the isolated Smart Compact v9 candidate."""

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
CANDIDATE_PROFILE = (
    ROOT / "benchmarks" / "experiments" / "v9-candidate" / "profile.config.toml"
)
CANDIDATE_POLICY = (
    ROOT / "benchmarks" / "experiments" / "v9-candidate" / "SKILL.md"
)
V8_ARMS = ("v8-no-spark", "v8-spark-forced", "v8-spark-auto")
CONTROL_ARMS = ("standard-no-spark", "v6-no-spark")
CANDIDATE_SPARK_AVAILABLE_INSTRUCTION = """
Spark availability does not itself justify delegation. Apply the profile's positive-expected-return gate before inspecting candidate worker paths. If the gate passes, spawn the exact `spark_worker` role as the first relevant tool, before reading worker-owned paths, with context forking disabled and a brief containing partition identifiers first, exclusive paths or inputs, the task, and the result contract. If the gate does not pass, stay local and do not probe. Never substitute another role.
"""


def validate_wrapper_args(argv: Sequence[str]) -> tuple[str, ...]:
    """Require explicit v8 evaluator arms and forbid profile substitution."""
    arms: list[str] = []
    index = 0
    while index < len(argv):
        value = argv[index]
        if value == "--v8-profile" or value.startswith("--v8-profile="):
            raise ValueError("--v8-profile is forbidden by the v9 candidate experiment")
        if value == "--arm":
            index += 1
            if index >= len(argv) or argv[index].startswith("--"):
                raise ValueError("--arm requires a v8 evaluator arm")
            arms.append(argv[index])
        elif value.startswith("--arm="):
            arms.append(value.split("=", 1)[1])
        index += 1

    if not arms:
        raise ValueError("the v9 candidate requires at least one explicit --arm")
    forbidden = [arm for arm in arms if arm in CONTROL_ARMS]
    if forbidden:
        raise ValueError(f"control arms are forbidden: {', '.join(forbidden)}")
    unknown = [arm for arm in arms if arm not in V8_ARMS]
    if unknown:
        raise ValueError(f"unsupported v9 candidate arms: {', '.join(unknown)}")
    return tuple(arms)


@contextlib.contextmanager
def configured_candidate_arms() -> Iterator[None]:
    """Temporarily bind candidate paths and the evidence-gated auto preflight."""
    if not CANDIDATE_PROFILE.is_file() or not CANDIDATE_POLICY.is_file():
        raise ValueError("v9 candidate profile and policy must both exist")
    original_specs = {arm: benchmark_v8.ARM_SPECS[arm] for arm in V8_ARMS}
    original_preflight = benchmark_v8.SPARK_AVAILABLE_INSTRUCTION
    try:
        for arm, current in original_specs.items():
            benchmark_v8.ARM_SPECS[arm] = benchmark_v8.ArmSpec(
                name=current.name,
                profile_path=CANDIDATE_PROFILE,
                policy_path=CANDIDATE_POLICY,
                spark_enabled=current.spark_enabled,
                multi_agent=current.multi_agent,
                skill_input=current.skill_input,
                routing_mode=current.routing_mode,
            )
        benchmark_v8.SPARK_AVAILABLE_INSTRUCTION = (
            CANDIDATE_SPARK_AVAILABLE_INSTRUCTION
        )
        yield
    finally:
        benchmark_v8.ARM_SPECS.update(original_specs)
        benchmark_v8.SPARK_AVAILABLE_INSTRUCTION = original_preflight


def main(argv: Sequence[str] | None = None) -> int:
    selected = list(sys.argv[1:] if argv is None else argv)
    try:
        validate_wrapper_args(selected)
        previous_argv = sys.argv
        with configured_candidate_arms():
            try:
                sys.argv = [previous_argv[0], *selected]
                return benchmark_v8.main()
            finally:
                sys.argv = previous_argv
    except (OSError, ValueError) as error:
        print(f"benchmark-v9-candidate: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
