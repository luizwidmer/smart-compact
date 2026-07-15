#!/usr/bin/env python3
"""Run v8 evaluator arms with Smart Compact v9 candidate revision 2."""

from __future__ import annotations

import contextlib
import sys
from collections.abc import Iterator, Sequence
from pathlib import Path

if __package__:
    from . import benchmark_v8
    from .benchmark_v9_candidate import validate_wrapper_args
else:
    import benchmark_v8
    from benchmark_v9_candidate import validate_wrapper_args


ROOT = Path(__file__).parents[1]
CANDIDATE_PROFILE = (
    ROOT / "benchmarks" / "experiments" / "v9-candidate-r2" / "profile.config.toml"
)
CANDIDATE_POLICY = (
    ROOT / "benchmarks" / "experiments" / "v9-candidate-r2" / "SKILL.md"
)
V8_ARMS = ("v8-no-spark", "v8-spark-forced", "v8-spark-auto")
CANDIDATE_SPARK_AVAILABLE_INSTRUCTION = """
Spark is available, but availability is not an obligation to spawn. Stay local even when the task asks for an available worker if the assignment is read-only inspection of six or fewer small structured files that the parent must edit or integrate; one batched parent read is cheaper. Otherwise spawn only when the accepted handoff replaces material parent work and comparable evidence or explicit parent-allowance priority makes the expected return positive. When spawning, use the exact `spark_worker` role as the first relevant tool before reading worker-owned paths, disable context forking, begin the brief with partition identifiers, and provide exclusive paths or inputs, the task, and the result contract. Never substitute another role or probe after choosing local execution.
"""


@contextlib.contextmanager
def configured_candidate_arms() -> Iterator[None]:
    """Temporarily bind revision-2 paths and its auto-only routing gate."""
    if not CANDIDATE_PROFILE.is_file() or not CANDIDATE_POLICY.is_file():
        raise ValueError("v9 candidate r2 profile and policy must both exist")
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
        print(f"benchmark-v9-candidate-r2: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
