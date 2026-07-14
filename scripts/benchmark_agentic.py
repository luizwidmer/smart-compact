#!/usr/bin/env python3
"""Run hermetic real-world-style workloads with paired Spark and no-Spark arms."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import random
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
import tomllib
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path, PurePosixPath
from typing import Any

if __package__:
    from .install_spark_agent import SPARK_MODEL, available_models
    from .open_app_task import (
        AppServerClient,
        AppTaskError,
        default_profile_path,
        default_codex_home,
        load_profile,
        resolve_codex,
        thread_start_params,
    )
    from .rtk_trace_audit import audit_commands
else:
    from install_spark_agent import SPARK_MODEL, available_models
    from open_app_task import (
        AppServerClient,
        AppTaskError,
        default_profile_path,
        default_codex_home,
        load_profile,
        resolve_codex,
        thread_start_params,
    )
    from rtk_trace_audit import audit_commands


ROOT = Path(__file__).parents[1]
DEFAULT_CASES = ROOT / "benchmarks" / "agentic-cases.json"
INSTALLED_SKILL = Path.home() / ".agents" / "skills" / "smart-compact" / "SKILL.md"
ARMS = ("spark", "no-spark")
TOOL_ITEM_TYPES = {
    "collabAgentToolCall",
    "commandExecution",
    "dynamicToolCall",
    "fileChange",
    "mcpToolCall",
    "webSearch",
}
USAGE_KEYS = (
    "inputTokens",
    "cachedInputTokens",
    "outputTokens",
    "reasoningOutputTokens",
    "totalTokens",
)
BENCHMARK_RTK_INSTRUCTION = (
    "Benchmark constraint: every shell command must start with literal rtk; "
    "use rtk proxy when raw output is required and retain rtk in acceptance commands. "
    "The task already starts in its exact target working directory: never run cd or "
    "chdir in a shell command, and pass any directory through the tool workdir field. "
    "If the shell cannot launch rtk itself, stop and report that wrapper failure. If a "
    "wrapped command fails, diagnose or retry only with another rtk-prefixed command; "
    "never use raw shell or an absolute binary path. "
    "If you delegate, copy this complete constraint into the child task because the child "
    "does not inherit it implicitly."
)


def load_cases(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise ValueError("agentic cases must use schema_version 1")
    cases = payload.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("agentic cases must contain a non-empty cases list")
    required = {
        "id",
        "split",
        "category",
        "inspired_by",
        "offload_expected",
        "human_minutes",
        "prompt",
        "acceptance_command",
        "allowed_changes",
        "seed_files",
        "gold_files",
        "hidden_checks",
    }
    seen: set[str] = set()
    for case in cases:
        if not isinstance(case, dict) or set(case) != required:
            raise ValueError(f"invalid case fields: {case.get('id') if isinstance(case, dict) else case!r}")
        case_id = case["id"]
        if not isinstance(case_id, str) or not case_id or case_id in seen:
            raise ValueError(f"invalid or duplicate case id: {case_id!r}")
        seen.add(case_id)
        if case["split"] not in {"development", "held-out"}:
            raise ValueError(f"invalid split for {case_id}")
        if not isinstance(case["offload_expected"], bool):
            raise ValueError(f"offload_expected must be boolean for {case_id}")
        if not isinstance(case["seed_files"], dict) or not case["seed_files"]:
            raise ValueError(f"seed_files must be non-empty for {case_id}")
        for relative in set(case["seed_files"]) | set(case["gold_files"]):
            safe_relative_path(relative)
    return cases


def safe_relative_path(value: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts or ".." in path.parts:
        raise ValueError(f"unsafe fixture path: {value}")
    return path


def write_files(root: Path, files: dict[str, str]) -> None:
    for relative, content in files.items():
        path = root.joinpath(*safe_relative_path(relative).parts)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def initialize_git(root: Path) -> None:
    commands = (
        ["git", "init", "-q"],
        ["git", "add", "."],
        [
            "git",
            "-c",
            "user.name=Smart Compact Benchmark",
            "-c",
            "user.email=benchmark@example.invalid",
            "commit",
            "-qm",
            "fixture baseline",
        ],
    )
    for command in commands:
        subprocess.run(command, cwd=root, check=True, capture_output=True, text=True)


def prepare_workspace(case: dict[str, Any], parent: Path) -> Path:
    workspace = parent / case["id"]
    workspace.mkdir(parents=True, exist_ok=False)
    write_files(workspace, case["seed_files"])
    initialize_git(workspace)
    return workspace


def prepare_codex_home(target: Path, spark_enabled: bool) -> Path:
    """Create an isolated authenticated home, adding the Spark role only to its arm."""
    source = default_codex_home()
    target.mkdir(parents=True, exist_ok=False, mode=0o700)
    auth = source / "auth.json"
    if not auth.is_file():
        raise AppTaskError(f"Codex authentication file not found: {auth}")
    shutil.copy2(auth, target / "auth.json")
    (target / "auth.json").chmod(0o600)
    for filename in ("installation_id", "models_cache.json"):
        candidate = source / filename
        if candidate.is_file():
            shutil.copy2(candidate, target / filename)
    if spark_enabled:
        agent = source / "agents" / "spark-worker.toml"
        if not agent.is_file():
            raise AppTaskError(f"Spark agent is not installed: {agent}")
        agents = target / "agents"
        agents.mkdir(mode=0o700)
        shutil.copy2(agent, agents / "spark-worker.toml")
        (agents / "spark-worker.toml").chmod(0o600)
    return target


def apply_gold(case: dict[str, Any], workspace: Path) -> None:
    write_files(workspace, case["gold_files"])


def arm_config(profile: dict[str, Any], arm: str) -> dict[str, Any]:
    if arm not in ARMS:
        raise ValueError(f"unknown arm: {arm}")
    config = copy.deepcopy(profile)
    # Isolate the profile policy from this machine's global/project AGENTS.md chain.
    config["project_doc_max_bytes"] = 0
    developer = config.get("developer_instructions", "")
    if not isinstance(developer, str):
        raise ValueError("profile developer_instructions must be a string when present")
    config["developer_instructions"] = f"{developer.rstrip()}\n\n{BENCHMARK_RTK_INSTRUCTION}\n"
    skills = config.setdefault("skills", {})
    if not isinstance(skills, dict):
        raise ValueError("profile skills must be a table when present")
    skill_config = skills.setdefault("config", [])
    if not isinstance(skill_config, list):
        raise ValueError("profile skills.config must be a list when present")
    skill_config.append({"path": str(INSTALLED_SKILL), "enabled": False})
    features = config.setdefault("features", {})
    if not isinstance(features, dict):
        raise ValueError("profile features must be a table when present")
    features["multi_agent"] = arm == "spark"
    return config


def run_command(argv: list[str], cwd: Path, timeout: float = 120.0) -> dict[str, Any]:
    started = time.monotonic()
    try:
        completed = subprocess.run(
            argv,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "ok": completed.returncode == 0,
            "returncode": completed.returncode,
            "duration_seconds": round(time.monotonic() - started, 3),
            "output": (completed.stdout + completed.stderr)[-4000:],
        }
    except (OSError, subprocess.TimeoutExpired) as error:
        return {
            "ok": False,
            "returncode": None,
            "duration_seconds": round(time.monotonic() - started, 3),
            "output": str(error),
        }


def command_version(argv: list[str]) -> str | None:
    try:
        completed = subprocess.run(argv, capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return None
    lines = [
        line.strip()
        for line in (completed.stdout + completed.stderr).splitlines()
        if line.strip()
    ]
    return lines[-1] if completed.returncode == 0 and lines else None


def write_json_payload(path: Path, payload: dict[str, Any]) -> None:
    target = path.expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(target)


def run_check(check: dict[str, Any], workspace: Path) -> dict[str, Any]:
    check_type = check.get("type")
    if check_type == "command":
        result = run_command(check["argv"], workspace)
        return {"type": check_type, **result}
    path_value = check.get("path")
    if not isinstance(path_value, str):
        return {"type": check_type, "ok": False, "error": "missing path"}
    path = workspace.joinpath(*safe_relative_path(path_value).parts)
    if not path.is_file():
        return {"type": check_type, "path": path_value, "ok": False, "error": "missing file"}
    if check_type == "path_contains":
        return {
            "type": check_type,
            "path": path_value,
            "ok": check["text"] in path.read_text(encoding="utf-8"),
        }
    if check_type == "path_not_contains":
        return {
            "type": check_type,
            "path": path_value,
            "ok": check["text"] not in path.read_text(encoding="utf-8"),
        }
    if check_type == "json_equals":
        try:
            value = json.loads(path.read_text(encoding="utf-8"))[check["key"]]
        except (json.JSONDecodeError, KeyError, TypeError) as error:
            return {"type": check_type, "path": path_value, "ok": False, "error": str(error)}
        return {
            "type": check_type,
            "path": path_value,
            "key": check["key"],
            "ok": value == check["value"],
            "actual": value,
        }
    return {"type": check_type, "path": path_value, "ok": False, "error": "unknown check"}


def evaluate_case(case: dict[str, Any], workspace: Path) -> dict[str, Any]:
    checks = [run_check(check, workspace) for check in case["hidden_checks"]]
    passed = sum(bool(check["ok"]) for check in checks)
    total = len(checks)
    return {
        "passed": passed,
        "total": total,
        "score_pct": round(passed / total * 100, 1) if total else 0.0,
        "ok": passed == total,
        "checks": checks,
    }


def changed_paths(workspace: Path) -> list[str]:
    completed = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=workspace,
        check=True,
        capture_output=True,
        text=True,
    )
    paths: set[str] = set()
    for line in completed.stdout.splitlines():
        value = line[3:]
        if " -> " in value:
            value = value.split(" -> ", 1)[1]
        paths.add(value)
    return sorted(paths)


def usage_breakdown(value: object) -> dict[str, int] | None:
    if not isinstance(value, dict):
        return None
    if not all(isinstance(value.get(key), int) for key in USAGE_KEYS):
        return None
    normalized = {key: int(value[key]) for key in USAGE_KEYS}
    if any(number < 0 for number in normalized.values()):
        return None
    if normalized["cachedInputTokens"] > normalized["inputTokens"]:
        return None
    if normalized["reasoningOutputTokens"] > normalized["outputTokens"]:
        return None
    if normalized["totalTokens"] != normalized["inputTokens"] + normalized["outputTokens"]:
        return None
    return normalized


def delegation_briefs_ok(prompts: list[str], expected_children: int) -> bool:
    if expected_children == 0:
        return not prompts
    if len(prompts) != expected_children:
        return False
    for prompt in prompts:
        normalized = (
            prompt.lower()
            .replace("`", "")
            .replace("literal prefix rtk", "literal rtk")
        )
        quantified = any(
            f"{quantifier} shell command" in normalized
            or f"{quantifier} command string" in normalized
            for quantifier in ("all", "each", "every")
        )
        mandatory_prefix = any(
            phrase in normalized
            for phrase in (
                "must begin",
                "must start",
                "has to begin",
                "has to start",
                "first word must be",
                "first word has to be",
                "shell command must be literal rtk",
                "shell command has to be literal rtk",
            )
        )
        no_shell_cd = any(
            phrase in normalized
            for phrase in (
                "never run cd",
                "do not run cd",
                "must not run cd",
                "never use cd",
                "do not use cd",
                "cd/chdir is forbidden",
                "shell cd is forbidden",
            )
        )
        target_is_current = "already" in normalized and any(
            phrase in normalized for phrase in ("working directory", "target root", "cwd")
        )
        if not (
            quantified
            and mandatory_prefix
            and "literal rtk" in normalized
            and no_shell_cd
            and target_is_current
        ):
            return False
    return True


def acceptance_command_observed(commands: list[str], argv: list[str]) -> bool:
    expected = " ".join(argv)
    return bool(expected) and any(expected in command for command in commands)


def child_completion_ok(
    turn_statuses: dict[str, str | None], child_ids: list[str], expected_children: int
) -> bool:
    if expected_children == 0:
        return not child_ids
    if len(child_ids) != expected_children:
        return False
    return all(turn_statuses.get(child_id) == "completed" for child_id in child_ids)


def collect_turn(
    client: AppServerClient,
    parent_thread_id: str,
    turn_timeout: float,
) -> dict[str, Any]:
    started = time.monotonic()
    deadline = started + turn_timeout
    usage: dict[str, dict[str, int]] = {}
    item_counts: dict[str, Counter[str]] = defaultdict(Counter)
    tool_calls: dict[str, int] = defaultdict(int)
    child_ids: set[str] = set()
    child_paths: dict[str, str] = {}
    spawn_models: set[str] = set()
    child_states: dict[str, dict[str, str | None]] = {}
    final_messages: list[str] = []
    commands: dict[str, list[str]] = defaultdict(list)
    spawn_prompts: list[str] = []
    first_spawn_seconds: float | None = None
    turn_status: Any = None

    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise AppTaskError("timed out waiting for benchmark turn completion")
        notification = client.next_notification(remaining)
        method = notification.get("method")
        params = notification.get("params")
        if not isinstance(params, dict):
            continue
        thread_id = params.get("threadId")
        if method == "thread/tokenUsage/updated" and isinstance(thread_id, str):
            token_usage = params.get("tokenUsage")
            total = token_usage.get("total") if isinstance(token_usage, dict) else None
            normalized = usage_breakdown(total)
            if normalized is not None:
                usage[thread_id] = normalized
        if method == "item/completed" and isinstance(thread_id, str):
            item = params.get("item")
            if isinstance(item, dict):
                item_type = item.get("type")
                if isinstance(item_type, str):
                    item_counts[thread_id][item_type] += 1
                    if item_type in TOOL_ITEM_TYPES:
                        tool_calls[thread_id] += 1
                if thread_id == parent_thread_id and item_type == "agentMessage":
                    message = item.get("text")
                    if isinstance(message, str):
                        final_messages.append(message)
                if item_type == "commandExecution" and isinstance(item.get("command"), str):
                    commands[thread_id].append(item["command"])
                if item_type == "subAgentActivity" and item.get("kind") == "started":
                    child_id = item.get("agentThreadId")
                    agent_path = item.get("agentPath")
                    if isinstance(child_id, str):
                        child_ids.add(child_id)
                        if isinstance(agent_path, str):
                            child_paths[child_id] = agent_path
                        if first_spawn_seconds is None:
                            first_spawn_seconds = round(time.monotonic() - started, 3)
                if item_type == "collabAgentToolCall" and item.get("tool") == "spawnAgent":
                    model = item.get("model")
                    if isinstance(model, str):
                        spawn_models.add(model)
                    prompt = item.get("prompt")
                    if isinstance(prompt, str):
                        spawn_prompts.append(prompt)
                    for child_id in item.get("receiverThreadIds", []):
                        if isinstance(child_id, str):
                            child_ids.add(child_id)
                    if first_spawn_seconds is None:
                        first_spawn_seconds = round(time.monotonic() - started, 3)
                if item_type == "collabAgentToolCall":
                    states = item.get("agentsStates")
                    if isinstance(states, dict):
                        for agent_id, state in states.items():
                            if not isinstance(agent_id, str) or not isinstance(state, dict):
                                continue
                            status = state.get("status")
                            message = state.get("message")
                            child_states[agent_id] = {
                                "status": status if isinstance(status, str) else None,
                                "message": message if isinstance(message, str) else None,
                            }
        if method == "turn/completed" and thread_id == parent_thread_id:
            turn = params.get("turn")
            turn_status = turn.get("status") if isinstance(turn, dict) else None
            break

    roles: dict[str, str | None] = {}
    child_turn_statuses: dict[str, str | None] = {}
    child_turn_errors: dict[str, str | None] = {}
    for offset, child_id in enumerate(sorted(child_ids), start=100):
        result = client.request(offset, "thread/read", {"threadId": child_id, "includeTurns": True})
        thread = result.get("thread")
        role = thread.get("agentRole") if isinstance(thread, dict) else None
        roles[child_id] = role if isinstance(role, str) else None
        turns = thread.get("turns") if isinstance(thread, dict) else None
        latest = turns[-1] if isinstance(turns, list) and turns else None
        status = latest.get("status") if isinstance(latest, dict) else None
        error = latest.get("error") if isinstance(latest, dict) else None
        message = error.get("message") if isinstance(error, dict) else None
        child_turn_statuses[child_id] = status if isinstance(status, str) else None
        child_turn_errors[child_id] = message if isinstance(message, str) else None

    return {
        "turn_status": turn_status,
        "duration_seconds": round(time.monotonic() - started, 3),
        "final_message": final_messages[-1] if final_messages else None,
        "first_spawn_seconds": first_spawn_seconds,
        "child_thread_ids": sorted(child_ids),
        "child_paths": child_paths,
        "child_roles": roles,
        "child_turn_statuses": child_turn_statuses,
        "child_turn_errors": child_turn_errors,
        "spawn_models": sorted(spawn_models),
        "spawn_prompts": spawn_prompts,
        "child_states": child_states,
        "usage_by_thread": usage,
        "item_counts_by_thread": {
            thread_id: dict(sorted(counts.items())) for thread_id, counts in item_counts.items()
        },
        "tool_calls_by_thread": dict(tool_calls),
        "commands_by_thread": dict(commands),
    }


def validate_spark_agent(codex: str, timeout: float, parent_model: str) -> dict[str, str]:
    agent_path = Path.home() / ".codex" / "agents" / "spark-worker.toml"
    if not agent_path.is_file():
        raise AppTaskError(f"Spark agent is not installed: {agent_path}")
    agent = tomllib.loads(agent_path.read_text(encoding="utf-8"))
    if agent.get("name") != "spark_worker" or agent.get("model") != SPARK_MODEL:
        raise AppTaskError("installed Spark agent is not pinned to spark_worker / gpt-5.3-codex-spark")
    models = available_models(codex, timeout)
    if SPARK_MODEL not in models:
        raise AppTaskError(f"{SPARK_MODEL} is not in the local model catalog")
    if parent_model not in models:
        raise AppTaskError(f"{parent_model} is not in the local model catalog")
    return {
        "path": str(agent_path),
        "sha256": hashlib.sha256(agent_path.read_bytes()).hexdigest(),
        "model": SPARK_MODEL,
    }


def run_case_arm(
    *,
    case: dict[str, Any],
    arm: str,
    trial: int,
    workspace: Path,
    codex: str,
    profile: dict[str, Any],
    model: str,
    effort: str,
    response_timeout: float,
    turn_timeout: float,
    codex_home: Path,
) -> dict[str, Any]:
    config = arm_config(profile, arm)
    with AppServerClient(
        codex,
        response_timeout,
        config_overrides=[f"features.multi_agent={'true' if arm == 'spark' else 'false'}"],
        environment={"CODEX_HOME": str(codex_home)},
    ) as client:
        client.initialize()
        params = thread_start_params(workspace, config, ephemeral=True)
        params.update(
            {
                "model": model,
                "sandbox": "workspace-write",
                "approvalPolicy": "never",
            }
        )
        started = client.request(1, "thread/start", params)
        thread = started.get("thread")
        if not isinstance(thread, dict) or not isinstance(thread.get("id"), str):
            raise AppTaskError("thread/start did not return a thread id")
        parent_thread_id = thread["id"]
        client.request(
            2,
            "turn/start",
            {
                "threadId": parent_thread_id,
                "model": model,
                "effort": effort,
                "input": [{"type": "text", "text": case["prompt"]}],
            },
        )
        trace = collect_turn(client, parent_thread_id, turn_timeout)

    grade = evaluate_case(case, workspace)
    changed = changed_paths(workspace)
    allowed = set(case["allowed_changes"])
    scope_ok = bool(changed) and set(changed) <= allowed
    child_ids = trace["child_thread_ids"]
    roles = trace["child_roles"]
    spark_children = [
        child_id
        for child_id in child_ids
        if roles.get(child_id) == "spark_worker"
        or Path(trace["child_paths"].get(child_id, "")).name == "spark_worker"
    ]
    expected_children = 1 if arm == "spark" and case["offload_expected"] else 0
    routing_ok = len(child_ids) == expected_children and len(spark_children) == expected_children
    delegation_brief_ok = delegation_briefs_ok(trace["spawn_prompts"], expected_children)
    child_completed = child_completion_ok(
        trace["child_turn_statuses"], child_ids, expected_children
    )
    parent_commands = trace["commands_by_thread"].get(parent_thread_id, [])
    acceptance_observed = acceptance_command_observed(
        parent_commands, case["acceptance_command"]
    )
    usage = trace["usage_by_thread"]
    parent_usage = usage.get(parent_thread_id)
    child_usage = [usage.get(child_id) for child_id in child_ids]
    usage_complete = parent_usage is not None and all(value is not None for value in child_usage)
    command_values = [command for values in trace["commands_by_thread"].values() for command in values]
    rtk_audit = audit_commands(command_values)
    rtk_ok = bool(rtk_audit["compliant"])
    child_total = sum(value["totalTokens"] for value in child_usage if value is not None)
    parent_total = parent_usage["totalTokens"] if parent_usage is not None else None
    combined_total = parent_total + child_total if parent_total is not None else None
    success = bool(
        trace["turn_status"] == "completed"
        and grade["ok"]
        and scope_ok
        and routing_ok
        and delegation_brief_ok
        and child_completed
        and acceptance_observed
        and usage_complete
        and rtk_ok
    )
    return {
        "case_id": case["id"],
        "split": case["split"],
        "category": case["category"],
        "arm": arm,
        "trial": trial,
        "offload_expected": case["offload_expected"],
        "parent_thread_id": parent_thread_id,
        "success": success,
        "turn_status": trace["turn_status"],
        "grade": grade,
        "changed_paths": changed,
        "scope_ok": scope_ok,
        "routing_ok": routing_ok,
        "delegation_brief_ok": delegation_brief_ok,
        "child_completion_ok": child_completed,
        "child_states": trace["child_states"],
        "child_turn_statuses": trace["child_turn_statuses"],
        "child_turn_errors": trace["child_turn_errors"],
        "acceptance_observed": acceptance_observed,
        "expected_children": expected_children,
        "child_thread_ids": child_ids,
        "spark_child_thread_ids": spark_children,
        "child_roles": roles,
        "spawn_models": trace["spawn_models"],
        "spawn_prompts": trace["spawn_prompts"],
        "usage_complete": usage_complete,
        "rtk_ok": rtk_ok,
        "rtk_command_count": rtk_audit["shell_calls"],
        "rtk_violations": rtk_audit["violations"],
        "parent_usage": parent_usage,
        "child_usage": {child_id: usage.get(child_id) for child_id in child_ids},
        "parent_total_tokens": parent_total,
        "child_total_tokens": child_total,
        "combined_total_tokens": combined_total,
        "duration_seconds": trace["duration_seconds"],
        "first_spawn_seconds": trace["first_spawn_seconds"],
        "tool_calls_by_thread": trace["tool_calls_by_thread"],
        "commands_by_thread": trace["commands_by_thread"],
        "item_counts_by_thread": trace["item_counts_by_thread"],
        "final_message": trace["final_message"],
    }


def paired_metrics(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, int], dict[str, dict[str, Any]]] = defaultdict(dict)
    for result in results:
        grouped[(result["case_id"], result["trial"])][result["arm"]] = result
    pairs: list[dict[str, Any]] = []
    for (case_id, trial), arms in sorted(grouped.items()):
        spark = arms.get("spark")
        local = arms.get("no-spark")
        complete = spark is not None and local is not None
        valid = bool(
            complete
            and spark["success"]
            and local["success"]
            and spark["usage_complete"]
            and local["usage_complete"]
            and spark["grade"]["ok"]
            and local["grade"]["ok"]
        )
        pair: dict[str, Any] = {
            "case_id": case_id,
            "trial": trial,
            "complete": complete,
            "valid": valid,
        }
        if complete:
            spark_parent = spark["parent_total_tokens"]
            local_parent = local["parent_total_tokens"]
            pair.update(
                {
                    "quality_parity": spark["grade"]["score_pct"] == local["grade"]["score_pct"],
                    "spark_success": spark["success"],
                    "no_spark_success": local["success"],
                    "parent_token_reduction_pct": (
                        round((local_parent - spark_parent) / local_parent * 100, 1)
                        if local_parent and spark_parent is not None
                        else None
                    ),
                    "combined_token_overhead_pct": (
                        round(
                            (spark["combined_total_tokens"] - local["combined_total_tokens"])
                            / local["combined_total_tokens"]
                            * 100,
                            1,
                        )
                        if local["combined_total_tokens"] and spark["combined_total_tokens"] is not None
                        else None
                    ),
                    "wall_time_reduction_pct": round(
                        (local["duration_seconds"] - spark["duration_seconds"])
                        / local["duration_seconds"]
                        * 100,
                        1,
                    )
                    if local["duration_seconds"]
                    else None,
                }
            )
        pairs.append(pair)
    return pairs


def aggregate_results(results: list[dict[str, Any]], pairs: list[dict[str, Any]]) -> dict[str, Any]:
    by_arm: dict[str, dict[str, Any]] = {}
    for arm in ARMS:
        rows = [row for row in results if row["arm"] == arm]
        token_rows = [row for row in rows if row["parent_total_tokens"] is not None]
        by_arm[arm] = {
            "runs": len(rows),
            "successes": sum(bool(row["success"]) for row in rows),
            "grade_passes": sum(bool(row["grade"]["ok"]) for row in rows),
            "routing_passes": sum(bool(row["routing_ok"]) for row in rows),
            "delegation_brief_passes": sum(bool(row["delegation_brief_ok"]) for row in rows),
            "child_completion_passes": sum(bool(row["child_completion_ok"]) for row in rows),
            "acceptance_passes": sum(bool(row["acceptance_observed"]) for row in rows),
            "scope_passes": sum(bool(row["scope_ok"]) for row in rows),
            "rtk_passes": sum(bool(row["rtk_ok"]) for row in rows),
            "usage_complete": sum(bool(row["usage_complete"]) for row in rows),
            "median_parent_tokens": statistics.median(row["parent_total_tokens"] for row in token_rows)
            if token_rows
            else None,
            "median_combined_tokens": statistics.median(row["combined_total_tokens"] for row in token_rows)
            if token_rows
            else None,
            "median_duration_seconds": statistics.median(row["duration_seconds"] for row in rows)
            if rows
            else None,
        }
    valid_pairs = [pair for pair in pairs if pair["valid"]]
    return {
        "by_arm": by_arm,
        "pairs": len(pairs),
        "valid_pairs": len(valid_pairs),
        "median_parent_token_reduction_pct": statistics.median(
            pair["parent_token_reduction_pct"] for pair in valid_pairs
        )
        if valid_pairs
        else None,
        "median_combined_token_overhead_pct": statistics.median(
            pair["combined_token_overhead_pct"] for pair in valid_pairs
        )
        if valid_pairs
        else None,
        "median_wall_time_reduction_pct": statistics.median(
            pair["wall_time_reduction_pct"] for pair in valid_pairs
        )
        if valid_pairs
        else None,
    }


def validate_fixtures(cases: list[dict[str, Any]]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="smart-compact-fixtures-") as temporary:
        root = Path(temporary)
        for case in cases:
            workspace = prepare_workspace(case, root)
            seed = evaluate_case(case, workspace)
            apply_gold(case, workspace)
            gold = evaluate_case(case, workspace)
            allowed = set(case["allowed_changes"])
            gold_paths = changed_paths(workspace)
            row = {
                "case_id": case["id"],
                "seed_score_pct": seed["score_pct"],
                "gold_score_pct": gold["score_pct"],
                "gold_scope_ok": bool(gold_paths) and set(gold_paths) <= allowed,
                "ok": not seed["ok"] and gold["ok"] and bool(gold_paths) and set(gold_paths) <= allowed,
            }
            rows.append(row)
    return {"ok": all(row["ok"] for row in rows), "cases": rows}


def sort_results(
    results: list[dict[str, Any]], case_ids: list[str]
) -> list[dict[str, Any]]:
    case_rank = {case_id: index for index, case_id in enumerate(case_ids)}
    arm_rank = {arm: index for index, arm in enumerate(ARMS)}
    return sorted(
        results,
        key=lambda row: (
            case_rank[row["case_id"]],
            row["trial"],
            arm_rank[row["arm"]],
        ),
    )


def run_case_trial(
    *,
    case: dict[str, Any],
    trial: int,
    arm_order: list[str],
    run_root: Path,
    codex: str,
    profile: dict[str, Any],
    model: str,
    effort: str,
    response_timeout: float,
    turn_timeout: float,
    keep_workspaces: bool,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for arm in arm_order:
        print(
            f"benchmark-agentic: start case={case['id']} trial={trial} arm={arm}",
            file=sys.stderr,
            flush=True,
        )
        workspace_parent = run_root / f"{case['id']}-trial-{trial}-{arm}"
        workspace: Path | None = None
        try:
            workspace_parent.mkdir(parents=True, exist_ok=False)
            workspace = prepare_workspace(case, workspace_parent)
            codex_home = prepare_codex_home(
                workspace_parent / ".codex-home",
                spark_enabled=arm == "spark",
            )
            result = run_case_arm(
                case=case,
                arm=arm,
                trial=trial,
                workspace=workspace,
                codex=codex,
                profile=profile,
                model=model,
                effort=effort,
                response_timeout=response_timeout,
                turn_timeout=turn_timeout,
                codex_home=codex_home,
            )
        except Exception as error:
            expected_children = 1 if arm == "spark" and case["offload_expected"] else 0
            result = {
                "case_id": case["id"],
                "split": case["split"],
                "category": case["category"],
                "arm": arm,
                "trial": trial,
                "offload_expected": case["offload_expected"],
                "parent_thread_id": None,
                "success": False,
                "turn_status": "runner_error",
                "grade": {
                    "ok": False,
                    "passed": 0,
                    "total": 0,
                    "score_pct": 0.0,
                    "checks": [],
                },
                "changed_paths": [],
                "scope_ok": False,
                "routing_ok": False,
                "delegation_brief_ok": False,
                "child_completion_ok": False,
                "child_states": {},
                "child_turn_statuses": {},
                "child_turn_errors": {},
                "acceptance_observed": False,
                "expected_children": expected_children,
                "child_thread_ids": [],
                "spark_child_thread_ids": [],
                "child_roles": {},
                "spawn_models": [],
                "spawn_prompts": [],
                "usage_complete": False,
                "rtk_ok": False,
                "rtk_command_count": 0,
                "rtk_violations": [],
                "parent_usage": None,
                "child_usage": {},
                "parent_total_tokens": None,
                "child_total_tokens": 0,
                "combined_total_tokens": None,
                "duration_seconds": 0.0,
                "first_spawn_seconds": None,
                "tool_calls_by_thread": {},
                "commands_by_thread": {},
                "item_counts_by_thread": {},
                "final_message": None,
                "runner_error": f"{type(error).__name__}: {error}",
            }
        result["workspace"] = (
            str(workspace) if keep_workspaces and workspace is not None else None
        )
        result["pair_arm_order"] = arm_order
        rows.append(result)
        print(
            "benchmark-agentic: finish "
            f"case={case['id']} trial={trial} arm={arm} "
            f"success={str(result['success']).lower()} "
            f"score={result['grade']['score_pct']} "
            f"children={len(result['child_thread_ids'])}",
            file=sys.stderr,
            flush=True,
        )
    return rows


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--case", action="append", default=[], help="case id; repeat to select")
    parser.add_argument("--split", choices=("all", "development", "held-out"), default="all")
    parser.add_argument("--arm", choices=("both", *ARMS), default="both")
    parser.add_argument("--repetitions", type=int, default=1)
    parser.add_argument("--jobs", type=int, default=1, help="concurrent case/trial pairs")
    parser.add_argument("--seed", type=int, default=20260714)
    parser.add_argument("--model", default="gpt-5.6-luna")
    parser.add_argument("--effort", default="high")
    parser.add_argument("--profile", type=Path, default=None)
    parser.add_argument("--codex", default=None)
    parser.add_argument("--response-timeout", type=float, default=30.0)
    parser.add_argument("--turn-timeout", type=float, default=900.0)
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
    cases_path = args.cases.expanduser().resolve()
    cases = load_cases(cases_path)
    if args.case:
        selected = set(args.case)
        cases = [case for case in cases if case["id"] in selected]
        missing = selected - {case["id"] for case in cases}
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

    codex = resolve_codex(args.codex)
    profile_path = (args.profile or default_profile_path()).expanduser().resolve()
    profile = load_profile(profile_path)
    selected_arms = list(ARMS if args.arm == "both" else (args.arm,))
    spark_agent = (
        validate_spark_agent(codex, args.response_timeout, args.model)
        if "spark" in selected_arms
        else None
    )
    run_root = args.work_root.expanduser().resolve() if args.work_root else Path(
        tempfile.mkdtemp(prefix="smart-compact-agentic-")
    )
    run_root.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    case_ids = [case["id"] for case in cases]
    pair_specs = [
        (
            case,
            trial,
            random.Random(f"{args.seed}:{case['id']}:{trial}").sample(
                selected_arms, k=len(selected_arms)
            ),
        )
        for case in cases
        for trial in range(1, args.repetitions + 1)
    ]
    jobs_used = min(args.jobs, len(pair_specs))
    execution_order = {
        f"{case['id']}:{trial}": order for case, trial, order in pair_specs
    }
    try:
        with ThreadPoolExecutor(max_workers=jobs_used) as executor:
            futures = [
                executor.submit(
                    run_case_trial,
                    case=case,
                    trial=trial,
                    arm_order=order,
                    run_root=run_root,
                    codex=codex,
                    profile=profile,
                    model=args.model,
                    effort=args.effort,
                    response_timeout=args.response_timeout,
                    turn_timeout=args.turn_timeout,
                    keep_workspaces=args.keep_workspaces,
                )
                for case, trial, order in pair_specs
            ]
            for future in as_completed(futures):
                results.extend(future.result())
                results = sort_results(results, case_ids)
                if args.output:
                    write_json_payload(
                        args.output,
                        {
                            "schema_version": 1,
                            "complete": False,
                            "publishable": False,
                            "generated_at": time.strftime(
                                "%Y-%m-%dT%H:%M:%SZ", time.gmtime()
                            ),
                            "jobs": jobs_used,
                            "wall_time_contended": jobs_used > 1,
                            "execution_order": execution_order,
                            "results": results,
                        },
                    )
        results = sort_results(results, case_ids)
        pairs = paired_metrics(results)
        all_success = all(result["success"] for result in results)
        all_pairs_valid = all(pair["valid"] for pair in pairs)
        publication_ready = bool(
            args.arm == "both"
            and args.repetitions >= 3
            and all_success
            and all_pairs_valid
        )
        payload = {
            "schema_version": 1,
            "complete": True,
            "publishable": publication_ready,
            "exploratory": args.repetitions < 3,
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "cases_sha256": hashlib.sha256(cases_path.read_bytes()).hexdigest(),
            "profile_path": str(profile_path),
            "profile_sha256": hashlib.sha256(profile_path.read_bytes()).hexdigest(),
            "disabled_skill_path": str(INSTALLED_SKILL),
            "codex": codex,
            "codex_version": command_version([codex, "--version"]),
            "rtk_version": command_version(["rtk", "--version"]),
            "model": args.model,
            "effort": args.effort,
            "jobs": jobs_used,
            "wall_time_contended": jobs_used > 1,
            "execution_order": execution_order,
            "spark_agent": spark_agent,
            "arms": selected_arms,
            "repetitions": args.repetitions,
            "seed": args.seed,
            "fixture_validation": fixture_validation,
            "results": results,
            "pairs": pairs,
            "aggregate": aggregate_results(results, pairs),
        }
        if args.output:
            write_json_payload(args.output, payload)
        rendered = json.dumps(payload, indent=2, sort_keys=True)
        print(rendered)
        return 0 if all_success and all_pairs_valid else 1
    except (AppTaskError, OSError, ValueError) as error:
        print(f"benchmark-agentic: {error}", file=sys.stderr)
        return 2
    finally:
        if not args.keep_workspaces and args.work_root is None:
            shutil.rmtree(run_root, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
