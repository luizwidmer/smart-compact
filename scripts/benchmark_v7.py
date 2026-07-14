#!/usr/bin/env python3
"""Run schema-v2 agentic benchmarks across frozen and candidate policy arms."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import queue
import random
import re
import shutil
import statistics
import sys
import tempfile
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any

if __package__:
    from .benchmark_agentic import (
        BENCHMARK_RTK_INSTRUCTION,
        INSTALLED_SKILL,
        TOOL_ITEM_TYPES,
        acceptance_command_observed,
        changed_paths,
        command_version,
        delegation_briefs_ok,
        evaluate_case,
        prepare_codex_home,
        prepare_workspace,
        safe_relative_path,
        usage_breakdown,
        validate_fixtures,
        validate_spark_agent,
        write_json_payload,
    )
    from .open_app_task import (
        AppServerClient,
        AppTaskError,
        load_profile,
        resolve_codex,
        thread_start_params,
    )
    from .rtk_trace_audit import audit_commands
else:
    from benchmark_agentic import (
        BENCHMARK_RTK_INSTRUCTION,
        INSTALLED_SKILL,
        TOOL_ITEM_TYPES,
        acceptance_command_observed,
        changed_paths,
        command_version,
        delegation_briefs_ok,
        evaluate_case,
        prepare_codex_home,
        prepare_workspace,
        safe_relative_path,
        usage_breakdown,
        validate_fixtures,
        validate_spark_agent,
        write_json_payload,
    )
    from open_app_task import (
        AppServerClient,
        AppTaskError,
        load_profile,
        resolve_codex,
        thread_start_params,
    )
    from rtk_trace_audit import audit_commands


ROOT = Path(__file__).parents[1]
DEFAULT_CASES = ROOT / "benchmarks" / "agentic-v7-development.json"
V6_PROFILE = ROOT / "benchmarks" / "profiles" / "v6.config.toml"
V6_POLICY = ROOT / "benchmarks" / "policies" / "v6" / "SKILL.md"
V7_PROFILE = ROOT / "profiles" / "smart-compact-v7.config.toml"
V7_POLICY = ROOT / "benchmarks" / "policies" / "v7" / "SKILL.md"
RANGE_KEYS = ("min", "max")
TERMINAL_TURN_STATUSES = {"completed", "failed", "interrupted"}
ACTIVE_AGENT_STATUSES = {"pendingInit", "running"}
CASE_KEYS = {
    "id",
    "split",
    "category",
    "inspired_by",
    "human_minutes",
    "prompt",
    "delegation",
    "acceptance_command",
    "allowed_changes",
    "seed_files",
    "gold_files",
    "hidden_checks",
}
DELEGATION_KEYS = {
    "mode",
    "worker_role",
    "worker_io",
    "spawned_workers",
    "useful_workers",
    "peak_concurrency",
    "duplicate_work_ratio_max",
    "expected_partitions",
    "parent_reserved_paths",
}
PARTITION_KEYS = {"id", "weight", "markers", "allowed_replication"}


@dataclass(frozen=True)
class ArmSpec:
    name: str
    profile_path: Path | None
    policy_path: Path | None
    spark_enabled: bool
    multi_agent: bool
    skill_input: bool = False


ARM_SPECS = {
    "standard-no-spark": ArmSpec("standard-no-spark", None, None, False, False),
    "v6-spark": ArmSpec("v6-spark", V6_PROFILE, V6_POLICY, True, True, True),
    "v7-no-spark": ArmSpec("v7-no-spark", V7_PROFILE, V7_POLICY, False, False),
    "v7-spark": ArmSpec("v7-spark", V7_PROFILE, V7_POLICY, True, True),
}
DEFAULT_ARMS = ("v6-spark", "v7-spark")
COMPARISON_SPECS = (
    ("v6_to_v7_spark", "v6-spark", "v7-spark", True),
    ("standard_to_v7", "standard-no-spark", "v7-spark", False),
    ("v7_no_spark_to_spark", "v7-no-spark", "v7-spark", False),
)


class DrainableAppServerClient(AppServerClient):
    """App-server client with a non-erroring notification poll for tail draining."""

    def poll_notification(self, timeout: float) -> dict[str, Any] | None:
        try:
            message = self.notifications.get(timeout=max(0.0, timeout))
        except queue.Empty:
            return None
        if message is None:
            raise AppTaskError(self._failure("app-server closed while draining notifications"))
        return message


def _is_int(value: object) -> bool:
    return type(value) is int


def _validate_range(value: object, label: str) -> dict[str, int]:
    if not isinstance(value, dict) or set(value) != set(RANGE_KEYS):
        raise ValueError(f"{label} must contain exactly min and max")
    minimum = value.get("min")
    maximum = value.get("max")
    if not _is_int(minimum) or not _is_int(maximum) or minimum < 0 or maximum < minimum:
        raise ValueError(f"invalid {label} range")
    return {"min": minimum, "max": maximum}


def load_cases(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or set(payload) != {"schema_version", "cases"}:
        raise ValueError("schema-v2 manifest must contain exactly schema_version and cases")
    if payload.get("schema_version") != 2:
        raise ValueError("agentic v7 cases must use schema_version 2")
    cases = payload.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("agentic v7 cases must contain a non-empty cases list")

    seen_cases: set[str] = set()
    for case in cases:
        if not isinstance(case, dict) or set(case) != CASE_KEYS:
            raise ValueError("invalid schema-v2 case fields")
        case_id = case["id"]
        if not isinstance(case_id, str) or not case_id or case_id in seen_cases:
            raise ValueError(f"invalid or duplicate case id: {case_id!r}")
        seen_cases.add(case_id)
        if case["split"] not in {"development", "held-out"}:
            raise ValueError(f"invalid split for {case_id}")
        if not isinstance(case["category"], str) or not case["category"]:
            raise ValueError(f"invalid category for {case_id}")
        if not isinstance(case["inspired_by"], list) or not all(
            isinstance(value, str) and value for value in case["inspired_by"]
        ):
            raise ValueError(f"invalid inspired_by for {case_id}")
        if not _is_int(case["human_minutes"]) or case["human_minutes"] <= 0:
            raise ValueError(f"invalid human_minutes for {case_id}")
        if not isinstance(case["prompt"], str) or not case["prompt"]:
            raise ValueError(f"invalid prompt for {case_id}")
        if not isinstance(case["acceptance_command"], list) or not case[
            "acceptance_command"
        ] or not all(isinstance(value, str) and value for value in case["acceptance_command"]):
            raise ValueError(f"invalid acceptance_command for {case_id}")
        if not isinstance(case["allowed_changes"], list) or not all(
            isinstance(value, str) and value for value in case["allowed_changes"]
        ):
            raise ValueError(f"invalid allowed_changes for {case_id}")
        if not isinstance(case["seed_files"], dict) or not case["seed_files"]:
            raise ValueError(f"seed_files must be non-empty for {case_id}")
        if not isinstance(case["gold_files"], dict) or not case["gold_files"]:
            raise ValueError(f"gold_files must be non-empty for {case_id}")
        for file_map in (case["seed_files"], case["gold_files"]):
            if not all(isinstance(key, str) and isinstance(value, str) for key, value in file_map.items()):
                raise ValueError(f"invalid file map for {case_id}")
        if not isinstance(case["hidden_checks"], list) or not case["hidden_checks"]:
            raise ValueError(f"hidden_checks must be non-empty for {case_id}")
        for relative in (
            set(case["seed_files"])
            | set(case["gold_files"])
            | set(case["allowed_changes"])
        ):
            safe_relative_path(relative)

        delegation = case["delegation"]
        if not isinstance(delegation, dict) or set(delegation) != DELEGATION_KEYS:
            raise ValueError(f"invalid delegation fields for {case_id}")
        if delegation["mode"] not in {"required_when_available", "forbidden"}:
            raise ValueError(f"invalid delegation mode for {case_id}")
        if delegation["worker_role"] != "spark_worker":
            raise ValueError(f"invalid worker role for {case_id}")
        if delegation["worker_io"] not in {"read_only", "path_disjoint"}:
            raise ValueError(f"invalid worker_io for {case_id}")
        spawned = _validate_range(delegation["spawned_workers"], f"{case_id}.spawned_workers")
        useful = _validate_range(delegation["useful_workers"], f"{case_id}.useful_workers")
        peak = _validate_range(delegation["peak_concurrency"], f"{case_id}.peak_concurrency")
        ratio = delegation["duplicate_work_ratio_max"]
        if isinstance(ratio, bool) or not isinstance(ratio, (int, float)) or not 0 <= ratio <= 1:
            raise ValueError(f"invalid duplicate_work_ratio_max for {case_id}")
        partitions = delegation["expected_partitions"]
        if not isinstance(partitions, list):
            raise ValueError(f"invalid expected_partitions for {case_id}")
        partition_ids: set[str] = set()
        for partition in partitions:
            if not isinstance(partition, dict) or set(partition) != PARTITION_KEYS:
                raise ValueError(f"invalid partition fields for {case_id}")
            partition_id = partition["id"]
            if (
                not isinstance(partition_id, str)
                or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", partition_id)
                or partition_id in partition_ids
            ):
                raise ValueError(f"invalid or duplicate partition id for {case_id}")
            partition_ids.add(partition_id)
            if not _is_int(partition["weight"]) or partition["weight"] <= 0:
                raise ValueError(f"invalid partition weight for {case_id}")
            if not isinstance(partition["markers"], list) or not partition["markers"] or not all(
                isinstance(marker, str) and marker for marker in partition["markers"]
            ):
                raise ValueError(f"invalid partition markers for {case_id}")
            if not _is_int(partition["allowed_replication"]) or partition[
                "allowed_replication"
            ] < 1:
                raise ValueError(f"invalid allowed_replication for {case_id}")
        reserved = delegation["parent_reserved_paths"]
        if not isinstance(reserved, list) or not all(
            isinstance(value, str) and value for value in reserved
        ):
            raise ValueError(f"invalid parent_reserved_paths for {case_id}")
        for relative in reserved:
            safe_relative_path(relative)

        if delegation["mode"] == "forbidden":
            if any(value != {"min": 0, "max": 0} for value in (spawned, useful, peak)):
                raise ValueError(f"forbidden case {case_id} must use zero worker ranges")
            if partitions:
                raise ValueError(f"forbidden case {case_id} cannot define partitions")
        else:
            if spawned["min"] < 1 or spawned["max"] > len(partitions):
                raise ValueError(f"positive worker range exceeds partitions for {case_id}")
            for label, value in (("useful", useful), ("peak", peak)):
                if value["min"] < spawned["min"] or value["max"] > spawned["max"]:
                    raise ValueError(f"{label} range must be within spawned range for {case_id}")
    return cases


def load_arm_profiles(selected_arms: list[str]) -> dict[str, dict[str, Any]]:
    profiles: dict[str, dict[str, Any]] = {}
    for arm in selected_arms:
        spec = ARM_SPECS[arm]
        if spec.profile_path is None:
            profiles[arm] = {}
        else:
            profiles[arm] = load_profile(spec.profile_path)
        if spec.policy_path is not None and not spec.policy_path.is_file():
            raise AppTaskError(f"policy snapshot not found: {spec.policy_path}")
    return profiles


def arm_metadata(selected_arms: list[str]) -> dict[str, dict[str, Any]]:
    metadata: dict[str, dict[str, Any]] = {}
    for arm in selected_arms:
        spec = ARM_SPECS[arm]
        row: dict[str, Any] = {
            "spark_enabled": spec.spark_enabled,
            "multi_agent": spec.multi_agent,
            "profile_path": str(spec.profile_path) if spec.profile_path else None,
            "policy_path": str(spec.policy_path) if spec.policy_path else None,
            "skill_input": spec.skill_input,
        }
        for name, path in (("profile", spec.profile_path), ("policy", spec.policy_path)):
            row[f"{name}_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest() if path else None
        metadata[arm] = row
    return metadata


def build_arm_config(spec: ArmSpec, profile: dict[str, Any]) -> dict[str, Any]:
    config = copy.deepcopy(profile)
    config["project_doc_max_bytes"] = 0
    developer = config.get("developer_instructions", "")
    if not isinstance(developer, str):
        raise ValueError("profile developer_instructions must be a string")
    fragments = [developer.rstrip()] if developer.strip() else []
    fragments.append(BENCHMARK_RTK_INSTRUCTION.rstrip())
    config["developer_instructions"] = "\n\n".join(fragments) + "\n"
    skills = config.setdefault("skills", {})
    if not isinstance(skills, dict):
        raise ValueError("profile skills must be a table")
    entries = skills.setdefault("config", [])
    if not isinstance(entries, list):
        raise ValueError("profile skills.config must be a list")
    disabled = {"path": str(INSTALLED_SKILL), "enabled": False}
    if disabled not in entries:
        entries.append(disabled)
    features = config.setdefault("features", {})
    if not isinstance(features, dict):
        raise ValueError("profile features must be a table")
    features["multi_agent"] = spec.multi_agent
    return config


def _new_trace() -> dict[str, Any]:
    return {
        "usage": {},
        "item_counts": defaultdict(Counter),
        "tool_calls": defaultdict(int),
        "commands": defaultdict(list),
        "file_changes": defaultdict(list),
        "child_ids": set(),
        "child_paths": {},
        "child_states": {},
        "spawn_records": {},
        "agent_messages": defaultdict(list),
        "child_final_messages": {},
        "final_messages": [],
        "first_spawn_seconds": None,
        "state_peak_concurrency": 0,
        "turn_status": None,
    }


def _record_notification(
    state: dict[str, Any], notification: dict[str, Any], parent_id: str, started: float
) -> None:
    method = notification.get("method")
    params = notification.get("params")
    if not isinstance(params, dict):
        return
    thread_id = params.get("threadId")
    if method == "thread/tokenUsage/updated" and isinstance(thread_id, str):
        token_usage = params.get("tokenUsage")
        total = token_usage.get("total") if isinstance(token_usage, dict) else None
        normalized = usage_breakdown(total)
        if normalized is not None:
            state["usage"][thread_id] = normalized
    if method == "item/completed" and isinstance(thread_id, str):
        item = params.get("item")
        if not isinstance(item, dict):
            return
        item_type = item.get("type")
        if isinstance(item_type, str):
            state["item_counts"][thread_id][item_type] += 1
            if item_type in TOOL_ITEM_TYPES:
                state["tool_calls"][thread_id] += 1
        if item_type == "agentMessage":
            message = item.get("text")
            if isinstance(message, str):
                state["agent_messages"][thread_id].append(message)
                if thread_id == parent_id:
                    state["final_messages"].append(message)
        if item_type == "commandExecution" and isinstance(item.get("command"), str):
            state["commands"][thread_id].append(item["command"])
        if item_type == "fileChange":
            for change in item.get("changes", []):
                path = change.get("path") if isinstance(change, dict) else None
                if isinstance(path, str):
                    state["file_changes"][thread_id].append(path)
        if item_type == "subAgentActivity" and item.get("kind") == "started":
            child_id = item.get("agentThreadId")
            if isinstance(child_id, str):
                state["child_ids"].add(child_id)
                path = item.get("agentPath")
                if isinstance(path, str):
                    state["child_paths"][child_id] = path
                if state["first_spawn_seconds"] is None:
                    state["first_spawn_seconds"] = round(time.monotonic() - started, 3)
        if item_type == "collabAgentToolCall":
            if item.get("tool") == "spawnAgent":
                receivers = [value for value in item.get("receiverThreadIds", []) if isinstance(value, str)]
                for child_id in receivers:
                    state["child_ids"].add(child_id)
                    record = state["spawn_records"].setdefault(child_id, {})
                    record["prompt"] = item.get("prompt") if isinstance(item.get("prompt"), str) else None
                    record["model"] = item.get("model") if isinstance(item.get("model"), str) else None
                if receivers and state["first_spawn_seconds"] is None:
                    state["first_spawn_seconds"] = round(time.monotonic() - started, 3)
            agent_states = item.get("agentsStates")
            if isinstance(agent_states, dict):
                active = 0
                for child_id, value in agent_states.items():
                    if not isinstance(child_id, str) or not isinstance(value, dict):
                        continue
                    status = value.get("status")
                    message = value.get("message")
                    state["child_states"][child_id] = {
                        "status": status if isinstance(status, str) else None,
                        "message": message if isinstance(message, str) else None,
                    }
                    if status in ACTIVE_AGENT_STATUSES:
                        active += 1
                state["state_peak_concurrency"] = max(state["state_peak_concurrency"], active)
    if method == "turn/completed" and thread_id == parent_id:
        turn = params.get("turn")
        state["turn_status"] = turn.get("status") if isinstance(turn, dict) else None


def _interval_peak(intervals: dict[str, dict[str, int | None]]) -> int:
    events: list[tuple[int, int]] = []
    now = int(time.time())
    for interval in intervals.values():
        started = interval.get("started_at")
        if not isinstance(started, int):
            continue
        completed = interval.get("completed_at")
        end = completed if isinstance(completed, int) else now
        events.append((started, 1))
        events.append((max(started, end), -1))
    current = 0
    peak = 0
    for _, delta in sorted(events, key=lambda value: (value[0], -value[1])):
        current += delta
        peak = max(peak, current)
    return peak


def _latest_agent_message(turns: object) -> str | None:
    if not isinstance(turns, list):
        return None
    for turn in reversed(turns):
        items = turn.get("items") if isinstance(turn, dict) else None
        if not isinstance(items, list):
            continue
        for item in reversed(items):
            if not isinstance(item, dict) or item.get("type") != "agentMessage":
                continue
            message = item.get("text")
            if isinstance(message, str) and message:
                return message
    return None


def _read_child_threads(
    client: DrainableAppServerClient,
    state: dict[str, Any],
    request_id: int,
) -> int:
    for child_id in sorted(state["child_ids"]):
        current_request_id = request_id
        request_id += 1
        try:
            result = client.request(
                current_request_id,
                "thread/read",
                {"threadId": child_id, "includeTurns": True},
            )
        except AppTaskError as error:
            state.setdefault("child_read_errors", {})[child_id] = str(error)
            continue
        thread = result.get("thread")
        role = thread.get("agentRole") if isinstance(thread, dict) else None
        state.setdefault("child_roles", {})[child_id] = role if isinstance(role, str) else None
        turns = thread.get("turns") if isinstance(thread, dict) else None
        latest = turns[-1] if isinstance(turns, list) and turns else None
        status = latest.get("status") if isinstance(latest, dict) else None
        final_message = _latest_agent_message(turns)
        if final_message is not None:
            state["child_final_messages"][child_id] = final_message
        error = latest.get("error") if isinstance(latest, dict) else None
        message = error.get("message") if isinstance(error, dict) else None
        state.setdefault("child_turn_statuses", {})[child_id] = status if isinstance(status, str) else None
        state.setdefault("child_turn_errors", {})[child_id] = message if isinstance(message, str) else None
        started_at = latest.get("startedAt") if isinstance(latest, dict) else None
        completed_at = latest.get("completedAt") if isinstance(latest, dict) else None
        state.setdefault("child_intervals", {})[child_id] = {
            "started_at": started_at if isinstance(started_at, int) else None,
            "completed_at": completed_at if isinstance(completed_at, int) else None,
        }
        state.setdefault("child_read_errors", {}).pop(child_id, None)
    return request_id


def collect_turn(
    client: DrainableAppServerClient,
    parent_thread_id: str,
    turn_timeout: float,
    drain_timeout: float,
) -> dict[str, Any]:
    started = time.monotonic()
    deadline = started + turn_timeout
    state = _new_trace()
    while state["turn_status"] is None:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise AppTaskError("timed out waiting for benchmark turn completion")
        _record_notification(state, client.next_notification(remaining), parent_thread_id, started)

    execution_duration = round(time.monotonic() - started, 3)
    drain_started = time.monotonic()
    drain_deadline = min(deadline, drain_started + max(0.0, drain_timeout))
    request_id = 100
    last_read = 0.0
    quiet_since: float | None = None
    while time.monotonic() < drain_deadline:
        remaining = drain_deadline - time.monotonic()
        notification = client.poll_notification(min(0.1, remaining))
        if notification is None:
            quiet_since = quiet_since or time.monotonic()
        else:
            quiet_since = None
            _record_notification(state, notification, parent_thread_id, started)
        now = time.monotonic()
        if now - last_read >= 0.25:
            request_id = _read_child_threads(client, state, request_id)
            last_read = now
        child_ids = sorted(state["child_ids"])
        statuses = state.get("child_turn_statuses", {})
        terminal = all(statuses.get(child_id) in TERMINAL_TURN_STATUSES for child_id in child_ids)
        telemetry = parent_thread_id in state["usage"] and all(
            child_id in state["usage"] for child_id in child_ids
        )
        if terminal and telemetry and quiet_since is not None and now - quiet_since >= 0.2:
            break
    request_id = _read_child_threads(client, state, request_id)
    del request_id

    child_ids = sorted(state["child_ids"])
    child_turn_statuses = state.get("child_turn_statuses", {})
    child_final_messages: dict[str, str] = {}
    for child_id in child_ids:
        if child_turn_statuses.get(child_id) != "completed":
            continue
        message = state["child_final_messages"].get(child_id)
        child_state = state["child_states"].get(child_id)
        if not isinstance(message, str) and isinstance(child_state, dict):
            state_message = child_state.get("message")
            if child_state.get("status") == "completed" and isinstance(state_message, str):
                message = state_message
        if not isinstance(message, str):
            observed = state["agent_messages"].get(child_id, [])
            message = observed[-1] if observed else None
        if isinstance(message, str):
            child_final_messages[child_id] = message
    interval_peak = _interval_peak(state.get("child_intervals", {}))
    return {
        "turn_status": state["turn_status"],
        "execution_duration_seconds": execution_duration,
        "drain_duration_seconds": round(time.monotonic() - drain_started, 3),
        "collection_duration_seconds": round(time.monotonic() - started, 3),
        "final_message": state["final_messages"][-1] if state["final_messages"] else None,
        "first_spawn_seconds": state["first_spawn_seconds"],
        "child_thread_ids": child_ids,
        "child_paths": state["child_paths"],
        "child_roles": state.get("child_roles", {}),
        "child_states": state["child_states"],
        "child_turn_statuses": child_turn_statuses,
        "child_final_messages": child_final_messages,
        "child_turn_errors": state.get("child_turn_errors", {}),
        "child_read_errors": state.get("child_read_errors", {}),
        "child_intervals": state.get("child_intervals", {}),
        "spawn_records": state["spawn_records"],
        "peak_concurrency": max(state["state_peak_concurrency"], interval_peak),
        "usage_by_thread": state["usage"],
        "item_counts_by_thread": {
            thread_id: dict(sorted(counts.items()))
            for thread_id, counts in state["item_counts"].items()
        },
        "tool_calls_by_thread": dict(state["tool_calls"]),
        "commands_by_thread": dict(state["commands"]),
        "file_changes_by_thread": dict(state["file_changes"]),
    }


def parse_partition_ids(prompt: str | None, expected_ids: set[str]) -> tuple[list[str], bool]:
    if not isinstance(prompt, str):
        return [], False
    found: list[str] = []
    syntax_ok = True
    marker_seen = False
    for line in prompt.splitlines():
        match = re.fullmatch(
            r"\s*partition_ids:\s*([A-Za-z0-9_.-]+(?:\s*,\s*[A-Za-z0-9_.-]+)*)\s*",
            line,
            flags=re.IGNORECASE,
        )
        if not match:
            if "partition_ids:" in line.lower():
                syntax_ok = False
            continue
        marker_seen = True
        values = [value.strip() for value in match.group(1).split(",")]
        if any(value not in expected_ids for value in values):
            syntax_ok = False
        found.extend(value for value in values if value in expected_ids)
    return sorted(set(found)), bool(marker_seen and syntax_ok)


def _in_range(value: int, expected: dict[str, int]) -> bool:
    return expected["min"] <= value <= expected["max"]


def _path_matches(path: str, relative: str) -> bool:
    normalized = path.replace("\\", "/").rstrip("/")
    target = relative.replace("\\", "/").strip("/")
    return normalized == target or normalized.endswith("/" + target)


def _text_mentions_path(text: str, relative: str) -> bool:
    normalized = text.replace("\\", "/")
    target = relative.replace("\\", "/").strip("/")
    if not target:
        return False
    trailing_boundary = r"(?=$|[\s,;:)\]}'\"`]|[.](?:\s|$))"
    pattern = rf"(?<![A-Za-z0-9_.-]){re.escape(target)}{trailing_boundary}"
    return re.search(pattern, normalized) is not None


def effective_delegation(case: dict[str, Any], spec: ArmSpec) -> dict[str, Any]:
    delegation = case["delegation"]
    enabled = spec.spark_enabled and delegation["mode"] == "required_when_available"
    if enabled:
        return {
            "spawned_workers": delegation["spawned_workers"],
            "useful_workers": delegation["useful_workers"],
            "peak_concurrency": delegation["peak_concurrency"],
            "expected_partitions": delegation["expected_partitions"],
        }
    zero = {"min": 0, "max": 0}
    return {
        "spawned_workers": zero,
        "useful_workers": zero,
        "peak_concurrency": zero,
        "expected_partitions": [],
    }


def evaluate_delegation(
    case: dict[str, Any],
    spec: ArmSpec,
    trace: dict[str, Any],
    parent_id: str | None = None,
) -> dict[str, Any]:
    delegation = case["delegation"]
    expected = effective_delegation(case, spec)
    child_ids = sorted(trace["child_thread_ids"])
    actual = len(child_ids)
    expected_role = delegation["worker_role"]
    role_ok = all(
        trace["child_roles"].get(child_id) == expected_role
        or Path(trace["child_paths"].get(child_id, "")).name == expected_role
        for child_id in child_ids
    )
    prompts = [
        trace["spawn_records"].get(child_id, {}).get("prompt") for child_id in child_ids
    ]
    valid_prompts = [prompt for prompt in prompts if isinstance(prompt, str)]
    brief_ok = len(valid_prompts) == actual and delegation_briefs_ok(valid_prompts, actual)

    partitions = {
        partition["id"]: partition for partition in expected["expected_partitions"]
    }
    expected_ids = set(partitions)
    assignments: dict[str, list[str]] = {}
    assignment_syntax_ok = True
    marker_ok = True
    for child_id in child_ids:
        prompt = trace["spawn_records"].get(child_id, {}).get("prompt")
        assigned, syntax_ok = parse_partition_ids(prompt, expected_ids)
        assignments[child_id] = assigned
        assignment_syntax_ok = assignment_syntax_ok and syntax_ok
        if assigned:
            marker_ok = marker_ok and all(
                all(marker in (prompt or "") for marker in partitions[partition_id]["markers"])
                for partition_id in assigned
            )
        elif expected_ids:
            marker_ok = False

    statuses = trace["child_turn_statuses"]
    commands = trace.get("commands_by_thread", {})
    final_messages = trace.get("child_final_messages", {})
    child_evidence_markers: dict[str, list[str]] = {}
    child_missing_evidence_markers: dict[str, list[str]] = {}
    child_evidence_coverage_ok: dict[str, bool] = {}
    for child_id in child_ids:
        assigned_markers = sorted(
            {
                marker
                for partition_id in assignments.get(child_id, [])
                for marker in partitions[partition_id]["markers"]
            }
        )
        evidence = [
            command
            for command in commands.get(child_id, [])
            if isinstance(command, str)
        ]
        final_message = final_messages.get(child_id)
        if statuses.get(child_id) == "completed" and isinstance(final_message, str):
            evidence.append(final_message)
        observed = [
            marker
            for marker in assigned_markers
            if any(_text_mentions_path(text, marker) for text in evidence)
        ]
        missing = sorted(set(assigned_markers) - set(observed))
        child_evidence_markers[child_id] = observed
        child_missing_evidence_markers[child_id] = missing
        child_evidence_coverage_ok[child_id] = bool(assigned_markers) and not missing

    replication = Counter(
        partition_id for assigned in assignments.values() for partition_id in assigned
    )
    claim_coverage_ok = set(replication) == expected_ids
    evidence_required = delegation["worker_io"] == "read_only" and bool(expected_ids)
    worker_evidence_ok = (
        bool(child_ids) and all(child_evidence_coverage_ok.values())
        if evidence_required
        else True
    )
    coverage_ok = claim_coverage_ok and worker_evidence_ok
    replication_ok = all(
        replication[partition_id] <= partition["allowed_replication"]
        for partition_id, partition in partitions.items()
    )
    assigned_weight = sum(
        partitions[partition_id]["weight"] * count
        for partition_id, count in replication.items()
    )
    unique_weight = sum(
        partition["weight"] for partition_id, partition in partitions.items() if replication[partition_id]
    )
    duplicate_weight = max(0, assigned_weight - unique_weight)
    duplicate_ratio = duplicate_weight / assigned_weight if assigned_weight else 0.0
    duplicate_ok = replication_ok and duplicate_ratio <= delegation["duplicate_work_ratio_max"]

    usage = trace["usage_by_thread"]
    item_counts = trace["item_counts_by_thread"]
    file_changes = trace["file_changes_by_thread"]
    child_io_ok: dict[str, bool] = {}
    for child_id in child_ids:
        changes = file_changes.get(child_id, [])
        if delegation["worker_io"] == "read_only":
            child_io_ok[child_id] = not changes
        else:
            allowed_paths = [
                marker
                for partition_id in assignments.get(child_id, [])
                for marker in partitions[partition_id]["markers"]
            ]
            reserved_write = any(
                _path_matches(path, reserved)
                for path in changes
                for reserved in delegation["parent_reserved_paths"]
            )
            assigned_write = all(
                any(_path_matches(path, allowed) for allowed in allowed_paths)
                for path in changes
            )
            child_io_ok[child_id] = not reserved_write and assigned_write
    useful_ids = [
        child_id
        for child_id in child_ids
        if statuses.get(child_id) == "completed"
        and usage.get(child_id) is not None
        and (
            item_counts.get(child_id, {}).get("agentMessage", 0) > 0
            or isinstance(final_messages.get(child_id), str)
        )
        and assignments.get(child_id)
        and child_io_ok.get(child_id, False)
        and (
            delegation["worker_io"] != "read_only"
            or child_evidence_coverage_ok.get(child_id, False)
        )
        and (
            delegation["worker_io"] == "read_only"
            or bool(file_changes.get(child_id, []))
        )
    ]
    useful_count = len(useful_ids)
    peak = int(trace.get("peak_concurrency") or 0)
    completion_ok = all(statuses.get(child_id) == "completed" for child_id in child_ids)
    spawned_range_ok = _in_range(actual, expected["spawned_workers"])
    useful_range_ok = _in_range(useful_count, expected["useful_workers"])
    peak_range_ok = _in_range(peak, expected["peak_concurrency"])
    io_ok = all(child_io_ok.values())
    worker_owned_paths = sorted(
        {
            marker
            for assigned in assignments.values()
            for partition_id in assigned
            for marker in partitions[partition_id]["markers"]
        }
    )
    parent_changes = file_changes.get(parent_id, []) if parent_id is not None else []
    overlap_paths = sorted(
        {
            path
            for path in parent_changes
            if any(_path_matches(path, owned) for owned in worker_owned_paths)
        }
    )
    overlap_ok = not overlap_paths if delegation["worker_io"] == "path_disjoint" else True
    parent_commands = commands.get(parent_id, []) if parent_id is not None else []
    parent_read_overlap_paths = sorted(
        {
            owned
            for owned in worker_owned_paths
            if any(
                isinstance(command, str) and _text_mentions_path(command, owned)
                for command in parent_commands
            )
        }
    )
    parent_read_overlap_ok = (
        not parent_read_overlap_paths
        if delegation["worker_io"] == "path_disjoint"
        else True
    )
    # Read-only workers need source markers in their briefs because no writes can
    # prove ownership. Path-disjoint workers are validated against observed
    # fileChange paths, so repeating every owned path in a brief is unnecessary
    # orchestration overhead.
    prompt_marker_gate = marker_ok if delegation["worker_io"] == "read_only" else True
    partition_ok = assignment_syntax_ok and prompt_marker_gate and coverage_ok
    routing_ok = bool(
        spawned_range_ok
        and role_ok
        and brief_ok
        and completion_ok
        and partition_ok
        and duplicate_ok
        and useful_range_ok
        and peak_range_ok
        and io_ok
        and overlap_ok
        and parent_read_overlap_ok
    )
    return {
        "effective_expectation": expected,
        "actual_spawned_workers": actual,
        "spawned_worker_range_ok": spawned_range_ok,
        "role_ok": role_ok,
        "delegation_brief_ok": brief_ok,
        "child_completion_ok": completion_ok,
        "partition_assignments": assignments,
        "partition_assignment_syntax_ok": assignment_syntax_ok,
        "partition_markers_ok": marker_ok,
        "partition_prompt_marker_gate_ok": prompt_marker_gate,
        "partition_claim_coverage_ok": claim_coverage_ok,
        "partition_coverage_ok": coverage_ok,
        "child_evidence_markers": child_evidence_markers,
        "child_missing_evidence_markers": child_missing_evidence_markers,
        "child_evidence_coverage_ok": child_evidence_coverage_ok,
        "worker_evidence_coverage_ok": worker_evidence_ok,
        "partition_replication": dict(sorted(replication.items())),
        "partition_replication_ok": replication_ok,
        "duplicate_work_ratio": round(duplicate_ratio, 6),
        "duplicate_work_ratio_ok": duplicate_ok,
        "useful_worker_ids": useful_ids,
        "useful_worker_count": useful_count,
        "useful_worker_rate": round(useful_count / actual, 6) if actual else 0.0,
        "useful_worker_range_ok": useful_range_ok,
        "peak_concurrency": peak,
        "peak_concurrency_range_ok": peak_range_ok,
        "worker_io_ok": io_ok,
        "child_io_ok": child_io_ok,
        "parent_worker_overlap_paths": overlap_paths,
        "parent_worker_overlap_ok": overlap_ok,
        "parent_worker_read_overlap_paths": parent_read_overlap_paths,
        "parent_worker_read_overlap_ok": parent_read_overlap_ok,
        "parent_reserved_prompt_ok": True,
        "routing_ok": routing_ok,
    }


def run_case_arm(
    *,
    case: dict[str, Any],
    spec: ArmSpec,
    trial: int,
    workspace: Path,
    codex: str,
    profile: dict[str, Any],
    model: str,
    effort: str,
    response_timeout: float,
    turn_timeout: float,
    drain_timeout: float,
    codex_home: Path,
) -> dict[str, Any]:
    config = build_arm_config(spec, profile)
    with DrainableAppServerClient(
        codex,
        response_timeout,
        config_overrides=[f"features.multi_agent={'true' if spec.multi_agent else 'false'}"],
        environment={"CODEX_HOME": str(codex_home)},
    ) as client:
        client.initialize()
        params = thread_start_params(workspace, config, ephemeral=True)
        params.update({"model": model, "sandbox": "workspace-write", "approvalPolicy": "never"})
        started = client.request(1, "thread/start", params)
        thread = started.get("thread")
        if not isinstance(thread, dict) or not isinstance(thread.get("id"), str):
            raise AppTaskError("thread/start did not return a thread id")
        parent_id = thread["id"]
        turn_input: list[dict[str, Any]] = []
        if spec.skill_input:
            if spec.policy_path is None:
                raise ValueError(f"{spec.name} requests a missing skill input")
            turn_input.append(
                {"type": "skill", "name": "codex-compact", "path": str(spec.policy_path)}
            )
        turn_input.append({"type": "text", "text": case["prompt"]})
        client.request(
            2,
            "turn/start",
            {
                "threadId": parent_id,
                "model": model,
                "effort": effort,
                "input": turn_input,
            },
        )
        trace = collect_turn(client, parent_id, turn_timeout, drain_timeout)

    grade = evaluate_case(case, workspace)
    changed = changed_paths(workspace)
    scope_ok = bool(changed) and set(changed) <= set(case["allowed_changes"])
    delegation = evaluate_delegation(case, spec, trace, parent_id)
    parent_commands = trace["commands_by_thread"].get(parent_id, [])
    acceptance_ok = acceptance_command_observed(parent_commands, case["acceptance_command"])
    usage = trace["usage_by_thread"]
    parent_usage = usage.get(parent_id)
    child_ids = trace["child_thread_ids"]
    child_usage = {child_id: usage.get(child_id) for child_id in child_ids}
    usage_complete = parent_usage is not None and all(value is not None for value in child_usage.values())
    commands = [command for values in trace["commands_by_thread"].values() for command in values]
    rtk_audit = audit_commands(commands)
    rtk_ok = bool(rtk_audit["compliant"])
    parent_tokens = parent_usage["totalTokens"] if parent_usage is not None else None
    child_tokens = sum(
        value["totalTokens"] for value in child_usage.values() if value is not None
    )
    combined_tokens = parent_tokens + child_tokens if parent_tokens is not None else None
    success = bool(
        trace["turn_status"] == "completed"
        and grade["ok"]
        and scope_ok
        and delegation["routing_ok"]
        and acceptance_ok
        and usage_complete
        and rtk_ok
    )
    return {
        "case_id": case["id"],
        "split": case["split"],
        "category": case["category"],
        "arm": spec.name,
        "trial": trial,
        "success": success,
        "turn_status": trace["turn_status"],
        "parent_thread_id": parent_id,
        "grade": grade,
        "changed_paths": changed,
        "scope_ok": scope_ok,
        "acceptance_observed": acceptance_ok,
        "usage_complete": usage_complete,
        "rtk_ok": rtk_ok,
        "rtk_command_count": rtk_audit["shell_calls"],
        "rtk_violations": rtk_audit["violations"],
        "parent_usage": parent_usage,
        "child_usage": child_usage,
        "parent_total_tokens": parent_tokens,
        "child_total_tokens": child_tokens,
        "combined_total_tokens": combined_tokens,
        "execution_duration_seconds": trace["execution_duration_seconds"],
        "drain_duration_seconds": trace["drain_duration_seconds"],
        "collection_duration_seconds": trace["collection_duration_seconds"],
        "first_spawn_seconds": trace["first_spawn_seconds"],
        "child_thread_ids": child_ids,
        "child_roles": trace["child_roles"],
        "child_turn_statuses": trace["child_turn_statuses"],
        "child_final_messages": trace["child_final_messages"],
        "child_turn_errors": trace["child_turn_errors"],
        "child_read_errors": trace["child_read_errors"],
        "spawn_records": trace["spawn_records"],
        "commands_by_thread": trace["commands_by_thread"],
        "file_changes_by_thread": trace["file_changes_by_thread"],
        "item_counts_by_thread": trace["item_counts_by_thread"],
        "tool_calls_by_thread": trace["tool_calls_by_thread"],
        "final_message": trace["final_message"],
        **delegation,
    }


def runner_error_result(case: dict[str, Any], arm: str, trial: int, error: BaseException) -> dict[str, Any]:
    return {
        "case_id": case["id"],
        "split": case["split"],
        "category": case["category"],
        "arm": arm,
        "trial": trial,
        "success": False,
        "turn_status": "runner_error",
        "runner_error": f"{type(error).__name__}: {error}",
        "parent_thread_id": None,
        "grade": {"ok": False, "passed": 0, "total": 0, "score_pct": 0.0, "checks": []},
        "changed_paths": [],
        "scope_ok": False,
        "acceptance_observed": False,
        "usage_complete": False,
        "rtk_ok": False,
        "rtk_command_count": 0,
        "rtk_violations": [],
        "parent_usage": None,
        "child_usage": {},
        "parent_total_tokens": None,
        "child_total_tokens": 0,
        "combined_total_tokens": None,
        "execution_duration_seconds": 0.0,
        "drain_duration_seconds": 0.0,
        "collection_duration_seconds": 0.0,
        "first_spawn_seconds": None,
        "child_thread_ids": [],
        "child_roles": {},
        "child_turn_statuses": {},
        "child_final_messages": {},
        "child_turn_errors": {},
        "child_read_errors": {},
        "spawn_records": {},
        "commands_by_thread": {},
        "file_changes_by_thread": {},
        "item_counts_by_thread": {},
        "tool_calls_by_thread": {},
        "final_message": None,
        "effective_expectation": {},
        "actual_spawned_workers": 0,
        "spawned_worker_range_ok": False,
        "role_ok": False,
        "delegation_brief_ok": False,
        "child_completion_ok": False,
        "partition_assignments": {},
        "partition_assignment_syntax_ok": False,
        "partition_markers_ok": False,
        "partition_prompt_marker_gate_ok": False,
        "partition_claim_coverage_ok": False,
        "partition_coverage_ok": False,
        "child_evidence_markers": {},
        "child_missing_evidence_markers": {},
        "child_evidence_coverage_ok": {},
        "worker_evidence_coverage_ok": False,
        "partition_replication": {},
        "partition_replication_ok": False,
        "duplicate_work_ratio": 0.0,
        "duplicate_work_ratio_ok": False,
        "useful_worker_ids": [],
        "useful_worker_count": 0,
        "useful_worker_rate": 0.0,
        "useful_worker_range_ok": False,
        "peak_concurrency": 0,
        "peak_concurrency_range_ok": False,
        "worker_io_ok": False,
        "child_io_ok": {},
        "parent_worker_overlap_paths": [],
        "parent_worker_overlap_ok": False,
        "parent_worker_read_overlap_paths": [],
        "parent_worker_read_overlap_ok": False,
        "parent_reserved_prompt_ok": False,
        "routing_ok": False,
    }


def execute_arm_job(
    *,
    case: dict[str, Any],
    arm: str,
    trial: int,
    order_index: int,
    run_root: Path,
    codex: str,
    profile: dict[str, Any],
    model: str,
    effort: str,
    response_timeout: float,
    turn_timeout: float,
    drain_timeout: float,
    keep_workspaces: bool,
) -> dict[str, Any]:
    workspace_parent = run_root / f"{case['id']}-trial-{trial}-{arm}"
    workspace: Path | None = None
    try:
        workspace_parent.mkdir(parents=True, exist_ok=False)
        workspace = prepare_workspace(case, workspace_parent)
        codex_home = prepare_codex_home(
            workspace_parent / ".codex-home", spark_enabled=ARM_SPECS[arm].spark_enabled
        )
        result = run_case_arm(
            case=case,
            spec=ARM_SPECS[arm],
            trial=trial,
            workspace=workspace,
            codex=codex,
            profile=profile,
            model=model,
            effort=effort,
            response_timeout=response_timeout,
            turn_timeout=turn_timeout,
            drain_timeout=drain_timeout,
            codex_home=codex_home,
        )
    except Exception as error:
        result = runner_error_result(case, arm, trial, error)
    result["workspace"] = str(workspace) if keep_workspaces and workspace is not None else None
    result["execution_order_index"] = order_index
    return result


def sort_results(
    results: list[dict[str, Any]], case_ids: list[str], selected_arms: list[str]
) -> list[dict[str, Any]]:
    case_rank = {case_id: index for index, case_id in enumerate(case_ids)}
    arm_rank = {arm: index for index, arm in enumerate(selected_arms)}
    return sorted(
        results,
        key=lambda row: (case_rank[row["case_id"]], row["trial"], arm_rank[row["arm"]]),
    )


def _reduction(baseline: int | float | None, candidate: int | float | None) -> float | None:
    if baseline in (None, 0) or candidate is None:
        return None
    return round((baseline - candidate) / baseline * 100, 3)


def _winner(baseline: dict[str, Any], candidate: dict[str, Any]) -> str:
    baseline_key = (
        int(bool(baseline["success"])),
        float(baseline["grade"]["score_pct"]),
        -(baseline["parent_total_tokens"] if baseline["parent_total_tokens"] is not None else float("inf")),
        -int(baseline["actual_spawned_workers"]),
    )
    candidate_key = (
        int(bool(candidate["success"])),
        float(candidate["grade"]["score_pct"]),
        -(candidate["parent_total_tokens"] if candidate["parent_total_tokens"] is not None else float("inf")),
        -int(candidate["actual_spawned_workers"]),
    )
    if candidate_key > baseline_key:
        return "candidate"
    if baseline_key > candidate_key:
        return "baseline"
    return "tie"


def comparison_rows(
    results: list[dict[str, Any]], selected_arms: list[str]
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, int], dict[str, dict[str, Any]]] = defaultdict(dict)
    for result in results:
        grouped[(result["case_id"], result["trial"])][result["arm"]] = result
    rows: list[dict[str, Any]] = []
    selected = set(selected_arms)
    for name, baseline_arm, candidate_arm, primary in COMPARISON_SPECS:
        if baseline_arm not in selected or candidate_arm not in selected:
            continue
        for (case_id, trial), arms in sorted(grouped.items()):
            baseline = arms.get(baseline_arm)
            candidate = arms.get(candidate_arm)
            complete = baseline is not None and candidate is not None
            row: dict[str, Any] = {
                "comparison": name,
                "primary": primary,
                "primary_efficiency_metric": "parent_tokens_saved_per_spawned_worker",
                "primary_efficiency_value": None,
                "case_id": case_id,
                "trial": trial,
                "baseline_arm": baseline_arm,
                "candidate_arm": candidate_arm,
                "complete": complete,
            }
            if complete:
                assert baseline is not None and candidate is not None
                baseline_parent = baseline["parent_total_tokens"]
                candidate_parent = candidate["parent_total_tokens"]
                saved = (
                    baseline_parent - candidate_parent
                    if baseline_parent is not None and candidate_parent is not None
                    else None
                )
                spawned = int(candidate["actual_spawned_workers"])
                useful = int(candidate["useful_worker_count"])
                saved_per_spawned = (
                    round(saved / spawned, 3) if saved is not None and spawned else None
                )
                saved_per_useful = (
                    round(saved / useful, 3) if saved is not None and useful else None
                )
                row.update(
                    {
                        "baseline_success": baseline["success"],
                        "candidate_success": candidate["success"],
                        "both_success": baseline["success"] and candidate["success"],
                        "quality_delta_points": round(
                            candidate["grade"]["score_pct"] - baseline["grade"]["score_pct"], 3
                        ),
                        "parent_tokens_observed": baseline_parent is not None and candidate_parent is not None,
                        "parent_tokens_saved": saved,
                        "parent_token_reduction_pct": _reduction(baseline_parent, candidate_parent),
                        "parent_tokens_saved_per_spawned_worker": saved_per_spawned,
                        "parent_tokens_saved_per_useful_worker": saved_per_useful,
                        "primary_efficiency_value": saved_per_spawned,
                        "spawned_worker_count": spawned,
                        "worker_count": spawned,
                        "useful_worker_count": useful,
                        "combined_token_reduction_pct": _reduction(
                            baseline["combined_total_tokens"], candidate["combined_total_tokens"]
                        ),
                        "latency_reduction_pct": _reduction(
                            baseline["execution_duration_seconds"],
                            candidate["execution_duration_seconds"],
                        ),
                        "selection_winner": _winner(baseline, candidate),
                    }
                )
            rows.append(row)
    return rows


def _median(values: list[int | float | None]) -> int | float | None:
    observed = [value for value in values if value is not None]
    return statistics.median(observed) if observed else None


def aggregate_comparisons(rows: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["comparison"]].append(row)
    output: dict[str, Any] = {}
    for name, assigned in grouped.items():
        complete = [row for row in assigned if row["complete"]]
        token_rows = [row for row in complete if row.get("parent_tokens_observed")]
        curves: list[dict[str, Any]] = []
        by_count: dict[int, list[dict[str, Any]]] = defaultdict(list)
        for row in complete:
            by_count[int(row["spawned_worker_count"])].append(row)
        for spawned_worker_count, count_rows in sorted(by_count.items()):
            count_token_rows = [row for row in count_rows if row.get("parent_tokens_observed")]
            curves.append(
                {
                    "spawned_worker_count": spawned_worker_count,
                    "worker_count": spawned_worker_count,
                    "runs": len(count_rows),
                    "candidate_successes": sum(bool(row["candidate_success"]) for row in count_rows),
                    "parent_token_pairs": len(count_token_rows),
                    "median_parent_tokens_saved": _median(
                        [row.get("parent_tokens_saved") for row in count_token_rows]
                    ),
                    "median_parent_token_reduction_pct": _median(
                        [row.get("parent_token_reduction_pct") for row in count_token_rows]
                    ),
                    "median_saved_per_spawned_worker": _median(
                        [row.get("parent_tokens_saved_per_spawned_worker") for row in count_token_rows]
                    ),
                    "median_primary_efficiency": _median(
                        [row.get("primary_efficiency_value") for row in count_token_rows]
                    ),
                    "median_saved_per_useful_worker": _median(
                        [row.get("parent_tokens_saved_per_useful_worker") for row in count_token_rows]
                    ),
                }
            )
        output[name] = {
            "primary": bool(assigned[0]["primary"]),
            "primary_efficiency_metric": "parent_tokens_saved_per_spawned_worker",
            "baseline_arm": assigned[0]["baseline_arm"],
            "candidate_arm": assigned[0]["candidate_arm"],
            "assigned_pairs": len(assigned),
            "complete_pairs": len(complete),
            "baseline_successes": sum(bool(row["baseline_success"]) for row in complete),
            "candidate_successes": sum(bool(row["candidate_success"]) for row in complete),
            "both_success": sum(bool(row["both_success"]) for row in complete),
            "parent_token_pairs": len(token_rows),
            "median_parent_tokens_saved": _median(
                [row.get("parent_tokens_saved") for row in token_rows]
            ),
            "median_parent_token_reduction_pct": _median(
                [row.get("parent_token_reduction_pct") for row in token_rows]
            ),
            "median_saved_per_spawned_worker": _median(
                [row.get("parent_tokens_saved_per_spawned_worker") for row in token_rows]
            ),
            "median_primary_efficiency": _median(
                [row.get("primary_efficiency_value") for row in token_rows]
            ),
            "median_saved_per_useful_worker": _median(
                [row.get("parent_tokens_saved_per_useful_worker") for row in token_rows]
            ),
            "median_spawned_worker_count": _median(
                [row.get("spawned_worker_count") for row in complete]
            ),
            "median_worker_count": _median(
                [row.get("spawned_worker_count") for row in complete]
            ),
            "spawned_worker_count_curve": curves,
            "worker_count_curve": curves,
        }
    return output


def aggregate_arms(results: list[dict[str, Any]], selected_arms: list[str]) -> dict[str, Any]:
    by_arm: dict[str, Any] = {}
    ranking: list[dict[str, Any]] = []
    for arm in selected_arms:
        rows = [row for row in results if row["arm"] == arm]
        token_rows = [row for row in rows if row["parent_total_tokens"] is not None]
        median_spawned_workers = _median([row["actual_spawned_workers"] for row in rows])
        summary = {
            "runs": len(rows),
            "successes": sum(bool(row["success"]) for row in rows),
            "grade_passes": sum(bool(row["grade"]["ok"]) for row in rows),
            "routing_passes": sum(bool(row["routing_ok"]) for row in rows),
            "usage_complete": sum(bool(row["usage_complete"]) for row in rows),
            "median_parent_tokens": _median([row["parent_total_tokens"] for row in token_rows]),
            "median_child_tokens": _median([row["child_total_tokens"] for row in token_rows]),
            "median_combined_tokens": _median([row["combined_total_tokens"] for row in token_rows]),
            "median_spawned_worker_count": median_spawned_workers,
            "median_worker_count": median_spawned_workers,
            "median_useful_worker_count": _median([row["useful_worker_count"] for row in rows]),
            "median_useful_worker_rate": _median([row["useful_worker_rate"] for row in rows]),
            "median_peak_concurrency": _median([row["peak_concurrency"] for row in rows]),
        }
        by_arm[arm] = summary
        mean_score = statistics.fmean(row["grade"]["score_pct"] for row in rows) if rows else 0.0
        ranking.append(
            {
                "arm": arm,
                "successes": summary["successes"],
                "mean_quality_score": round(mean_score, 3),
                "median_parent_tokens": summary["median_parent_tokens"],
                "median_spawned_worker_count": summary["median_spawned_worker_count"],
                "median_worker_count": summary["median_worker_count"],
            }
        )
    ranking.sort(
        key=lambda row: (
            -row["successes"],
            -row["mean_quality_score"],
            row["median_parent_tokens"] if row["median_parent_tokens"] is not None else float("inf"),
            row["median_spawned_worker_count"]
            if row["median_spawned_worker_count"] is not None
            else float("inf"),
        )
    )
    for index, row in enumerate(ranking, start=1):
        row["rank"] = index
    return {"by_arm": by_arm, "selection_ranking": ranking}


def expected_result_keys(
    cases: list[dict[str, Any]], repetitions: int, selected_arms: list[str]
) -> set[tuple[str, int, str]]:
    return {
        (case["id"], trial, arm)
        for case in cases
        for trial in range(1, repetitions + 1)
        for arm in selected_arms
    }


def publication_status(
    results: list[dict[str, Any]], expected: set[tuple[str, int, str]], repetitions: int, jobs: int
) -> dict[str, bool]:
    observed = [(row["case_id"], row["trial"], row["arm"]) for row in results]
    matrix = len(observed) == len(set(observed)) and set(observed) == expected
    quality_coverage = matrix and all(row["grade"]["total"] > 0 for row in results)
    quality = bool(quality_coverage and repetitions >= 3)
    tokens = bool(quality and all(row["usage_complete"] for row in results))
    latency = bool(tokens and jobs == 1)
    return {
        "matrix_complete": matrix,
        "quality_publishable": quality,
        "token_publishable": tokens,
        "latency_publishable": latency,
    }


def checkpoint_payload(
    *,
    results: list[dict[str, Any]],
    selected_arms: list[str],
    execution_order: list[dict[str, Any]],
    repetitions: int,
    jobs: int,
) -> dict[str, Any]:
    return {
        "schema_version": 2,
        "complete": False,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "arms": selected_arms,
        "repetitions": repetitions,
        "jobs": jobs,
        "wall_time_contended": jobs > 1,
        "execution_order": execution_order,
        "completed_arms": len(results),
        "results": results,
    }


def matrix_exit_code(results: list[dict[str, Any]], matrix_complete: bool) -> int:
    return 0 if matrix_complete and all(row["success"] for row in results) else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--case", action="append", default=[])
    parser.add_argument("--split", choices=("all", "development", "held-out"), default="all")
    parser.add_argument("--arm", action="append", choices=tuple(ARM_SPECS), default=[])
    parser.add_argument("--repetitions", type=int, default=1)
    parser.add_argument("--jobs", type=int, default=3)
    parser.add_argument("--seed", type=int, default=20260714)
    parser.add_argument("--model", default="gpt-5.6-luna")
    parser.add_argument("--effort", default="high")
    parser.add_argument("--codex", default=None)
    parser.add_argument("--response-timeout", type=float, default=30.0)
    parser.add_argument("--turn-timeout", type=float, default=900.0)
    parser.add_argument("--drain-timeout", type=float, default=10.0)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--work-root", type=Path, default=None)
    parser.add_argument("--keep-workspaces", action="store_true")
    parser.add_argument("--validate-fixtures", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.repetitions < 1:
        raise SystemExit("--repetitions must be at least 1")
    if args.jobs < 1:
        raise SystemExit("--jobs must be at least 1")
    if args.drain_timeout < 0:
        raise SystemExit("--drain-timeout cannot be negative")
    cases_path = args.cases.expanduser().resolve()
    cases = load_cases(cases_path)
    if args.case:
        selected_case_ids = set(args.case)
        cases = [case for case in cases if case["id"] in selected_case_ids]
        missing = selected_case_ids - {case["id"] for case in cases}
        if missing:
            raise SystemExit(f"unknown case ids: {', '.join(sorted(missing))}")
    if args.split != "all":
        cases = [case for case in cases if case["split"] == args.split]
    if not cases:
        raise SystemExit("no cases selected")

    fixture_validation = validate_fixtures(cases)
    if args.validate_fixtures:
        print(json.dumps(fixture_validation, indent=2, sort_keys=True))
        return 0 if fixture_validation["ok"] else 1
    if not fixture_validation["ok"]:
        raise SystemExit("fixture validation failed")

    selected_arms = list(dict.fromkeys(args.arm or DEFAULT_ARMS))
    profiles = load_arm_profiles(selected_arms)
    codex = resolve_codex(args.codex)
    spark_agent = (
        validate_spark_agent(codex, args.response_timeout, args.model)
        if any(ARM_SPECS[arm].spark_enabled for arm in selected_arms)
        else None
    )
    run_root = args.work_root.expanduser().resolve() if args.work_root else Path(
        tempfile.mkdtemp(prefix="smart-compact-v7-")
    )
    run_root.mkdir(parents=True, exist_ok=True)
    case_ids = [case["id"] for case in cases]
    jobs_to_run = [
        {"case": case, "trial": trial, "arm": arm}
        for case in cases
        for trial in range(1, args.repetitions + 1)
        for arm in selected_arms
    ]
    random.Random(args.seed).shuffle(jobs_to_run)
    execution_order = [
        {
            "index": index,
            "case_id": job["case"]["id"],
            "trial": job["trial"],
            "arm": job["arm"],
        }
        for index, job in enumerate(jobs_to_run)
    ]
    jobs_used = min(args.jobs, len(jobs_to_run))
    results: list[dict[str, Any]] = []
    expected = expected_result_keys(cases, args.repetitions, selected_arms)
    try:
        with ThreadPoolExecutor(max_workers=jobs_used) as executor:
            futures = {
                executor.submit(
                    execute_arm_job,
                    case=job["case"],
                    arm=job["arm"],
                    trial=job["trial"],
                    order_index=index,
                    run_root=run_root,
                    codex=codex,
                    profile=profiles[job["arm"]],
                    model=args.model,
                    effort=args.effort,
                    response_timeout=args.response_timeout,
                    turn_timeout=args.turn_timeout,
                    drain_timeout=args.drain_timeout,
                    keep_workspaces=args.keep_workspaces,
                ): (job, index)
                for index, job in enumerate(jobs_to_run)
            }
            for future in as_completed(futures):
                job, index = futures[future]
                try:
                    result = future.result()
                except BaseException as error:
                    result = runner_error_result(job["case"], job["arm"], job["trial"], error)
                    result["workspace"] = None
                    result["execution_order_index"] = index
                results.append(result)
                results = sort_results(results, case_ids, selected_arms)
                if args.output:
                    write_json_payload(
                        args.output,
                        checkpoint_payload(
                            results=results,
                            selected_arms=selected_arms,
                            execution_order=execution_order,
                            repetitions=args.repetitions,
                            jobs=jobs_used,
                        ),
                    )

        results = sort_results(results, case_ids, selected_arms)
        comparisons = comparison_rows(results, selected_arms)
        publication = publication_status(results, expected, args.repetitions, jobs_used)
        payload = {
            "schema_version": 2,
            "complete": publication["matrix_complete"],
            "exploratory": args.repetitions < 3 or len(selected_arms) < 2,
            "publication_status": publication,
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "cases_path": str(cases_path),
            "cases_sha256": hashlib.sha256(cases_path.read_bytes()).hexdigest(),
            "arms": selected_arms,
            "arm_metadata": arm_metadata(selected_arms),
            "disabled_skill_path": str(INSTALLED_SKILL),
            "spark_agent": spark_agent,
            "codex": codex,
            "codex_version": command_version([codex, "--version"]),
            "rtk_version": command_version(["rtk", "--version"]),
            "model": args.model,
            "effort": args.effort,
            "repetitions": args.repetitions,
            "jobs": jobs_used,
            "wall_time_contended": jobs_used > 1,
            "seed": args.seed,
            "execution_order": execution_order,
            "fixture_validation": fixture_validation,
            "results": results,
            "comparisons": comparisons,
            "comparison_aggregate": aggregate_comparisons(comparisons),
            "arm_aggregate": aggregate_arms(results, selected_arms),
        }
        if args.output:
            write_json_payload(args.output, payload)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return matrix_exit_code(results, publication["matrix_complete"])
    finally:
        if not args.keep_workspaces and args.work_root is None:
            shutil.rmtree(run_root, ignore_errors=True)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AppTaskError, OSError, ValueError, json.JSONDecodeError) as error:
        print(f"benchmark-v7: {error}", file=sys.stderr)
        raise SystemExit(2)
