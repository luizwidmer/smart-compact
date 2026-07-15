#!/usr/bin/env python3
"""Run and fully reap the frozen 42-cell v8 verbose-treatment matrix."""

from __future__ import annotations

import argparse
import json
import os
import re
import signal
import subprocess
import sys
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Sequence


ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / "scripts" / "benchmark_v8_verbose.py"
CONFIRMATION_CASES = ROOT / "benchmarks" / "agentic-v8-confirmation.json"
CALCULATOR_CASES = ROOT / "benchmarks" / "agentic-v8-legacy-calculator.json"
RELAY_CASES = ROOT / "benchmarks" / "agentic-v8-legacy-relay-bench.json"
DEFAULT_OUTPUT_DIR = ROOT / "benchmarks" / "results" / "raw" / "v8-verbose"
SEED = 20260721
MAX_CONCURRENT = 4
SPARK_MODEL = "gpt-5.3-codex-spark"
VERBOSE_PROFILE_SUFFIX = "benchmarks/experiments/v8-verbose/profile.config.toml"
VERBOSE_POLICY_SUFFIX = "benchmarks/experiments/v8-verbose/SKILL.md"
V8_NO_SPARK = "v8-no-spark"
V8_FORCED = "v8-spark-forced"
V8_AUTO = "v8-spark-auto"

NON_ANCHOR_CASES = (
    "release-readiness",
    "incident-triage",
    "offline-advisory-triage",
    "ci-matrix-root-cause",
    "tenant-config-drift",
    "support-credit-adjudication",
    "permission-scope-regression",
    "multi-service-contract-rollout",
    "policy-bound-batch-update",
)


@dataclass(frozen=True)
class Setting:
    slug: str
    model: str
    effort: str


SETTINGS = (
    Setting("sol-medium", "gpt-5.6-sol", "medium"),
    Setting("sol-high", "gpt-5.6-sol", "high"),
    Setting("luna-xhigh", "gpt-5.6-luna", "xhigh"),
    Setting("luna-max", "gpt-5.6-luna", "max"),
)


@dataclass(frozen=True)
class Invocation:
    name: str
    manifest: Path
    case_ids: tuple[str, ...]
    arms: tuple[str, ...]
    setting: Setting
    jobs: int
    output: Path

    @property
    def cells(self) -> int:
        return len(self.case_ids) * len(self.arms)

    def expected_keys(self) -> set[tuple[str, int, str]]:
        return {(case_id, 1, arm) for case_id in self.case_ids for arm in self.arms}

    def command(self, python: str = sys.executable) -> list[str]:
        command = [python, str(WRAPPER), "--cases", str(self.manifest)]
        for case_id in self.case_ids:
            command.extend(("--case", case_id))
        for arm in self.arms:
            command.extend(("--arm", arm))
        command.extend(
            (
                "--repetitions",
                "1",
                "--jobs",
                str(self.jobs),
                "--external-contention",
                "--seed",
                str(SEED),
                "--model",
                self.setting.model,
                "--effort",
                self.setting.effort,
                "--output",
                str(self.output),
            )
        )
        return command


@dataclass(frozen=True)
class CompletedInvocation:
    invocation: Invocation
    returncode: int
    tolerated_protocol_exit: bool


class MatrixFailure(RuntimeError):
    """A child launch, artifact, or treatment-integrity failure."""


def build_matrix(output_dir: Path = DEFAULT_OUTPUT_DIR) -> list[Invocation]:
    anchors = (
        ("legacy-calculator", CALCULATOR_CASES),
        ("legacy-relay-bench", RELAY_CASES),
        ("monorepo-sdk-migration", CONFIRMATION_CASES),
    )
    invocations = [
        Invocation(
            name=f"{case_id}-{setting.slug}",
            manifest=manifest,
            case_ids=(case_id,),
            arms=(V8_NO_SPARK, V8_FORCED),
            setting=setting,
            jobs=1,
            output=output_dir / f"v8-verbose-{case_id}-{setting.slug}.json",
        )
        for case_id, manifest in anchors
        for setting in SETTINGS
    ]
    invocations.append(
        Invocation(
            name="agentic-non-anchor-luna-xhigh",
            manifest=CONFIRMATION_CASES,
            case_ids=NON_ANCHOR_CASES,
            arms=(V8_NO_SPARK, V8_AUTO),
            setting=SETTINGS[2],
            jobs=4,
            output=output_dir / "v8-verbose-agentic-non-anchor-luna-xhigh.json",
        )
    )
    if len(invocations) != 13 or sum(item.cells for item in invocations) != 42:
        raise AssertionError("internal verbose matrix must remain 13 invocations / 42 cells")
    return invocations


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _path_ends_with(value: Any, suffix: str) -> bool:
    return isinstance(value, str) and value.replace("\\", "/").endswith(suffix)


def _metadata_integrity(payload: dict[str, Any], arms: tuple[str, ...]) -> bool:
    metadata = payload.get("arm_metadata")
    if not isinstance(metadata, dict) or set(metadata) != set(arms):
        return False
    expected = {
        V8_NO_SPARK: ("none", False),
        V8_FORCED: ("forced", True),
        V8_AUTO: ("auto", True),
    }
    for arm in arms:
        row = metadata.get(arm)
        if not isinstance(row, dict):
            return False
        routing_mode, spark_enabled = expected[arm]
        if row.get("routing_mode") != routing_mode or row.get("spark_enabled") is not spark_enabled:
            return False
        if not _path_ends_with(row.get("profile_path"), VERBOSE_PROFILE_SUFFIX):
            return False
        if not _path_ends_with(row.get("policy_path"), VERBOSE_POLICY_SUFFIX):
            return False
        if not _is_sha256(row.get("profile_sha256")) or not _is_sha256(
            row.get("policy_sha256")
        ):
            return False
    return True


def _range_contains(value: int, expected: Any) -> bool:
    if not isinstance(expected, dict):
        return False
    minimum = expected.get("min")
    maximum = expected.get("max")
    return (
        isinstance(minimum, int)
        and value >= minimum
        and (maximum is None or isinstance(maximum, int) and value <= maximum)
    )


def _children_match(
    row: dict[str, Any], *, origin: str, native_agent_role: bool
) -> bool:
    actual = row.get("actual_spawned_workers")
    child_roles = row.get("child_roles")
    records = row.get("spawn_records")
    if not isinstance(actual, int) or actual < 1:
        return False
    if not isinstance(child_roles, dict) or not isinstance(records, dict):
        return False
    if len(child_roles) != actual or set(child_roles) != set(records):
        return False
    return all(
        child_roles.get(child_id) == "spark_worker"
        and isinstance(record, dict)
        and record.get("role") == "spark_worker"
        and record.get("model") == SPARK_MODEL
        and record.get("origin") == origin
        and record.get("native_agent_role") is native_agent_role
        for child_id, record in records.items()
    )


def _treatment_integrity(row: dict[str, Any]) -> bool:
    arm = row.get("arm")
    actual = row.get("actual_spawned_workers")
    if arm == V8_NO_SPARK:
        return (
            actual == 0
            and row.get("child_total_tokens") == 0
            and row.get("child_thread_ids") == []
            and row.get("routing_mode") == "none"
        )
    if arm == V8_FORCED:
        return row.get("routing_mode") == "forced" and _children_match(
            row, origin="harness_thread", native_agent_role=False
        )
    if arm == V8_AUTO:
        expected = row.get("effective_expectation", {}).get("spawned_workers")
        if not isinstance(actual, int) or not _range_contains(actual, expected):
            return False
        if row.get("routing_mode") != "auto":
            return False
        if actual == 0:
            return row.get("child_total_tokens") == 0 and row.get("child_thread_ids") == []
        return _children_match(row, origin="parent_agent", native_agent_role=True)
    return False


def validate_artifact(invocation: Invocation, returncode: int) -> CompletedInvocation:
    try:
        payload = json.loads(invocation.output.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise MatrixFailure(f"{invocation.name}: unreadable artifact: {error}") from error
    if not isinstance(payload, dict) or payload.get("schema_version") != 3:
        raise MatrixFailure(f"{invocation.name}: artifact is not schema version 3")
    results = payload.get("results")
    if not isinstance(results, list) or not all(isinstance(row, dict) for row in results):
        raise MatrixFailure(f"{invocation.name}: artifact results are missing")
    observed = {(row.get("case_id"), row.get("trial"), row.get("arm")) for row in results}
    complete = (
        payload.get("complete") is True
        and payload.get("publication_status", {}).get("matrix_complete") is True
        and observed == invocation.expected_keys()
        and len(results) == invocation.cells
        and payload.get("arms") == list(invocation.arms)
        and payload.get("model") == invocation.setting.model
        and payload.get("effort") == invocation.setting.effort
        and payload.get("repetitions") == 1
        and payload.get("seed") == SEED
        and payload.get("wall_time_contended") is True
    )
    if not complete:
        raise MatrixFailure(f"{invocation.name}: incomplete or mismatched artifact")
    if not _metadata_integrity(payload, invocation.arms):
        raise MatrixFailure(f"{invocation.name}: verbose treatment metadata mismatch")

    hard_gate = all(
        row.get("task_pass") is True
        and row.get("acceptance_observed") is True
        and row.get("no_active_children") is True
        and row.get("turn_status") == "completed"
        and isinstance(row.get("scope_ok"), bool)
        and isinstance(row.get("usage_complete"), bool)
        and isinstance(row.get("parent_total_tokens"), int)
        and row["parent_total_tokens"] > 0
        and isinstance(row.get("parent_usage"), dict)
        and row["parent_usage"].get("totalTokens") == row["parent_total_tokens"]
        and _treatment_integrity(row)
        for row in results
    )
    if not hard_gate:
        raise MatrixFailure(f"{invocation.name}: task, parent usage, or treatment gate failed")

    if returncode == 0:
        if not all(row.get("protocol_pass") is True and row.get("success") is True for row in results):
            raise MatrixFailure(f"{invocation.name}: exit 0 conflicts with protocol results")
        return CompletedInvocation(invocation, returncode, False)
    if returncode == 1:
        protocol_only = all(
            row.get("success") is row.get("protocol_pass")
            and isinstance(row.get("success"), bool)
            for row in results
        ) and any(row.get("protocol_pass") is False for row in results)
        if protocol_only:
            return CompletedInvocation(invocation, returncode, True)
        raise MatrixFailure(f"{invocation.name}: exit 1 is not an isolated protocol miss")
    raise MatrixFailure(f"{invocation.name}: substantive child exit {returncode}")


def terminate_and_reap(processes: Sequence[Any], timeout: float = 10.0) -> None:
    for process in processes:
        if process.poll() is None:
            pid = getattr(process, "pid", None)
            if isinstance(pid, int):
                try:
                    os.killpg(pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
            else:
                process.terminate()
    for process in processes:
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            pid = getattr(process, "pid", None)
            if isinstance(pid, int):
                try:
                    os.killpg(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            else:
                process.kill()
            process.wait()


def run_matrix(
    invocations: Sequence[Invocation],
    *,
    max_concurrent: int = MAX_CONCURRENT,
    poll_interval: float = 0.25,
    python: str = sys.executable,
    popen: Callable[..., Any] = subprocess.Popen,
    sleep: Callable[[float], None] = time.sleep,
) -> list[CompletedInvocation]:
    if not 1 <= max_concurrent <= MAX_CONCURRENT:
        raise ValueError(f"max_concurrent must be between 1 and {MAX_CONCURRENT}")
    if poll_interval < 0:
        raise ValueError("poll_interval cannot be negative")
    pending = deque(invocations)
    running: dict[Any, Invocation] = {}
    completed: list[CompletedInvocation] = []
    try:
        while pending or running:
            while pending and len(running) < max_concurrent:
                invocation = pending.popleft()
                invocation.output.parent.mkdir(parents=True, exist_ok=True)
                process = popen(
                    invocation.command(python),
                    cwd=ROOT,
                    start_new_session=True,
                )
                running[process] = invocation
            progressed = False
            for process, invocation in list(running.items()):
                returncode = process.poll()
                if returncode is None:
                    continue
                process.wait()
                del running[process]
                completed.append(validate_artifact(invocation, returncode))
                progressed = True
            if not progressed and running:
                sleep(poll_interval)
    except BaseException:
        terminate_and_reap(list(running))
        raise
    return completed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--max-concurrent", type=int, default=MAX_CONCURRENT)
    parser.add_argument("--poll-interval", type=float, default=0.25)
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--print-plan", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    invocations = build_matrix(args.output_dir.expanduser().resolve())
    if args.print_plan:
        print(
            json.dumps(
                {
                    "invocations": len(invocations),
                    "cells": sum(item.cells for item in invocations),
                    "max_concurrent": args.max_concurrent,
                    "commands": [item.command(args.python) for item in invocations],
                },
                indent=2,
            )
        )
        return 0
    if not WRAPPER.is_file():
        raise SystemExit(f"verbose wrapper not found: {WRAPPER}")
    try:
        completed = run_matrix(
            invocations[:-1],
            max_concurrent=args.max_concurrent,
            poll_interval=args.poll_interval,
            python=args.python,
        )
        completed.extend(
            run_matrix(
                invocations[-1:],
                max_concurrent=1,
                poll_interval=args.poll_interval,
                python=args.python,
            )
        )
    except (MatrixFailure, OSError, ValueError) as error:
        print(f"v8-verbose-matrix: {error}", file=sys.stderr)
        return 2
    print(
        json.dumps(
            {
                "complete": len(completed) == len(invocations),
                "invocations": len(completed),
                "cells": sum(item.invocation.cells for item in completed),
                "tolerated_protocol_exits": sum(
                    item.tolerated_protocol_exit for item in completed
                ),
                "artifacts": [str(item.invocation.output) for item in completed],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
