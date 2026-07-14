#!/usr/bin/env python3
"""Run an ephemeral app-server workload and verify autonomous Spark delegation."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

if __package__:
    from .open_app_task import (
        AppServerClient,
        AppTaskError,
        default_profile_path,
        load_profile,
        resolve_codex,
        thread_start_params,
    )
else:
    from open_app_task import (
        AppServerClient,
        AppTaskError,
        default_profile_path,
        load_profile,
        resolve_codex,
        thread_start_params,
    )


DEFAULT_PROMPT = """Use $smart-compact. My explicit optimization goal is to preserve the parent-model allowance; for this smoke test I accept possible combined-token or latency overhead from one Spark sidecar. One bounded read-only sidecar has six exclusive files: README.md, scripts/install_smart_compact.py, tests/test_package_installer.py, benchmarks/agentic-cases.json, scripts/benchmark_agentic.py, and tests/test_agentic_benchmark.py. Audit those six files for package-versus-benchmark inventory inconsistencies while the parent independently reconciles SKILL.md with profiles/smart-compact.config.toml. Report only mismatches with exact paths, or state that both workstreams are consistent. Do not edit files."""


def default_skill_path() -> Path:
    installed = Path.home() / ".agents" / "skills" / "smart-compact" / "SKILL.md"
    checkout = Path(__file__).parents[1] / "SKILL.md"
    return installed if installed.is_file() else checkout


def spawn_record(notification: dict[str, Any]) -> dict[str, Any] | None:
    if notification.get("method") not in {"item/started", "item/completed"}:
        return None
    params = notification.get("params")
    item = params.get("item") if isinstance(params, dict) else None
    if not isinstance(item, dict):
        return None
    if item.get("type") != "collabAgentToolCall" or item.get("tool") != "spawnAgent":
        return None
    return {
        "id": item.get("id"),
        "model": item.get("model"),
        "status": item.get("status"),
        "receiver_thread_ids": item.get("receiverThreadIds", []),
    }


def started_subagent_ids(activities: list[dict[str, Any]], parent_thread_id: str) -> list[str]:
    return sorted(
        {
            activity["agent_thread_id"]
            for activity in activities
            if activity.get("kind") == "started"
            and isinstance(activity.get("agent_thread_id"), str)
            and activity["agent_thread_id"] != parent_thread_id
        }
    )


def benchmark_ok(result: dict[str, Any]) -> bool:
    """Require a completed parent turn and exactly one verified Spark child."""
    return bool(
        result.get("turn_status") == "completed"
        and result.get("spark_spawned")
        and result.get("spawn_count") == 1
        and result.get("final_message")
    )


def run_benchmark(
    codex: str,
    cwd: Path,
    config: dict[str, Any],
    skill: Path,
    prompt: str,
    response_timeout: float,
    turn_timeout: float,
) -> dict[str, Any]:
    with AppServerClient(codex, response_timeout) as client:
        client.initialize()
        started = client.request(
            1,
            "thread/start",
            thread_start_params(cwd, config, ephemeral=True),
        )
        thread = started.get("thread")
        if not isinstance(thread, dict) or not isinstance(thread.get("id"), str):
            raise AppTaskError("thread/start did not return a thread id")
        thread_id = thread["id"]
        client.request(
            2,
            "turn/start",
            {
                "threadId": thread_id,
                "input": [
                    {"type": "skill", "name": "smart-compact", "path": str(skill)},
                    {"type": "text", "text": prompt},
                ],
            },
        )

        deadline = time.monotonic() + turn_timeout
        spawns: dict[str, dict[str, Any]] = {}
        collab_calls: dict[str, dict[str, Any]] = {}
        subagent_activities: list[dict[str, Any]] = []
        item_types: dict[str, int] = {}
        agent_messages: list[str] = []
        turn_status: Any = None
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise AppTaskError("timed out waiting for benchmark turn completion")
            notification = client.next_notification(remaining)
            params = notification.get("params")
            item = params.get("item") if isinstance(params, dict) else None
            if isinstance(item, dict) and item.get("type") == "collabAgentToolCall":
                call_id = item.get("id")
                if isinstance(call_id, str):
                    collab_calls[call_id] = {
                        "id": call_id,
                        "tool": item.get("tool"),
                        "model": item.get("model"),
                        "status": item.get("status"),
                        "receiver_thread_ids": item.get("receiverThreadIds", []),
                    }
            if notification.get("method") == "item/completed":
                item_type = item.get("type") if isinstance(item, dict) else None
                if isinstance(item_type, str):
                    item_types[item_type] = item_types.get(item_type, 0) + 1
                if item_type == "agentMessage" and isinstance(item.get("text"), str):
                    agent_messages.append(item["text"])
                if item_type == "subAgentActivity":
                    subagent_activities.append(
                        {
                            "agent_path": item.get("agentPath"),
                            "agent_thread_id": item.get("agentThreadId"),
                            "kind": item.get("kind"),
                        }
                    )
            record = spawn_record(notification)
            if record is not None and isinstance(record["id"], str):
                previous = spawns.get(record["id"], {})
                spawns[record["id"]] = {
                    key: value if value not in (None, []) else previous.get(key, value)
                    for key, value in record.items()
                }
            if notification.get("method") == "turn/completed":
                params = notification.get("params")
                turn = params.get("turn") if isinstance(params, dict) else None
                turn_status = turn.get("status") if isinstance(turn, dict) else None
                break

        roles: set[str] = set()
        receiver_ids = {
            receiver_id
            for record in spawns.values()
            for receiver_id in record["receiver_thread_ids"]
            if isinstance(receiver_id, str)
        }
        receiver_ids.update(started_subagent_ids(subagent_activities, thread_id))
        for offset, receiver_id in enumerate(sorted(receiver_ids), start=10):
            result = client.request(
                offset,
                "thread/read",
                {"threadId": receiver_id, "includeTurns": False},
            )
            thread = result.get("thread")
            role = thread.get("agentRole") if isinstance(thread, dict) else None
            if isinstance(role, str):
                roles.add(role)

    records = list(spawns.values())
    models = sorted({record["model"] for record in records if isinstance(record["model"], str)})
    spawned_thread_ids = sorted(receiver_ids)
    activity_paths = {
        Path(activity["agent_path"]).name
        for activity in subagent_activities
        if isinstance(activity["agent_path"], str)
    }
    return {
        "thread_id": thread_id,
        "skill_path": str(skill),
        "turn_status": turn_status,
        "item_types": item_types,
        "final_message": agent_messages[-1] if agent_messages else None,
        "spawn_count": len(spawned_thread_ids),
        "models": models,
        "roles": sorted(roles),
        "spark_spawned": (
            "gpt-5.3-codex-spark" in models
            or "spark_worker" in roles
            or "spark_worker" in activity_paths
        ),
        "spawns": records,
        "collab_calls": list(collab_calls.values()),
        "subagent_activities": subagent_activities,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", type=Path, default=Path.cwd(), help="workspace path")
    parser.add_argument("--profile", type=Path, default=None, help="profile TOML path")
    parser.add_argument("--codex", default=None, help="Codex CLI executable or path")
    parser.add_argument("--skill", type=Path, default=None, help="Smart Compact SKILL.md path")
    parser.add_argument("--prompt", default=DEFAULT_PROMPT, help="benchmark prompt")
    parser.add_argument("--response-timeout", type=float, default=30.0)
    parser.add_argument("--turn-timeout", type=float, default=600.0)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    cwd = args.path.expanduser().resolve()
    profile = (args.profile or default_profile_path()).expanduser().resolve()
    skill = (args.skill or default_skill_path()).expanduser().resolve()
    if not skill.is_file():
        print(f"benchmark-spark-spawn: skill not found: {skill}", file=sys.stderr)
        return 2
    try:
        result = run_benchmark(
            resolve_codex(args.codex),
            cwd,
            load_profile(profile),
            skill,
            args.prompt,
            args.response_timeout,
            args.turn_timeout,
        )
    except AppTaskError as error:
        print(f"benchmark-spark-spawn: {error}", file=sys.stderr)
        return 2
    result["ok"] = benchmark_ok(result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
