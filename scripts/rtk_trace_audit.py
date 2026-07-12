#!/usr/bin/env python3
"""Reject benchmark rollouts that submit shell commands without RTK."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


EXEC_CALL = "tools.exec_command("
CMD_KEY = re.compile(r"(?:[\"']cmd[\"']|\bcmd)\s*:")


def _literal_after_cmd(source: str, start: int, end: int) -> str | None:
    match = CMD_KEY.search(source, start, end)
    if not match:
        return None
    position = match.end()
    while position < end and source[position].isspace():
        position += 1
    if position >= end or source[position] not in {'"', "'", "`"}:
        return None

    quote = source[position]
    position += 1
    command_start = position
    while position < end:
        character = source[position]
        if character == "\\":
            position += 2
            continue
        if character == quote:
            return source[command_start:position]
        position += 1
    return None


def extract_exec_commands(source: str) -> list[str | None]:
    """Extract literal cmd values, returning None for dynamic or malformed calls."""
    starts: list[int] = []
    position = 0
    while True:
        position = source.find(EXEC_CALL, position)
        if position < 0:
            break
        starts.append(position)
        position += len(EXEC_CALL)

    commands: list[str | None] = []
    for index, start in enumerate(starts):
        end = starts[index + 1] if index + 1 < len(starts) else len(source)
        commands.append(_literal_after_cmd(source, start, end))
    return commands


def _is_rtk(command: str) -> bool:
    stripped = command.lstrip()
    return stripped == "rtk" or stripped.startswith("rtk ")


def audit_rollout(path: Path) -> dict[str, object]:
    commands: list[str | None] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if record.get("type") != "response_item":
            continue
        payload = record.get("payload", {})

        if payload.get("type") == "custom_tool_call" and payload.get("name") == "exec":
            source = payload.get("input")
            if isinstance(source, str):
                commands.extend(extract_exec_commands(source))
        elif payload.get("type") == "function_call" and payload.get("name") == "exec_command":
            arguments = payload.get("arguments")
            try:
                decoded = json.loads(arguments) if isinstance(arguments, str) else arguments
            except json.JSONDecodeError:
                decoded = None
            command = decoded.get("cmd") if isinstance(decoded, dict) else None
            commands.append(command if isinstance(command, str) else None)

    violations = []
    for index, command in enumerate(commands, start=1):
        if command is None:
            violations.append({"shell_call": index, "reason": "command is not a literal"})
        elif not _is_rtk(command):
            violations.append(
                {
                    "shell_call": index,
                    "reason": "command does not start with rtk",
                    "command": command[:200],
                }
            )

    return {
        "rollout": str(path),
        "shell_calls": len(commands),
        "rtk_calls": sum(command is not None and _is_rtk(command) for command in commands),
        "violations": violations,
        "compliant": bool(commands) and not violations,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rollouts", nargs="+", type=Path)
    args = parser.parse_args()
    reports = [audit_rollout(path) for path in args.rollouts]
    print(json.dumps(reports, indent=2))
    return 0 if all(report["compliant"] for report in reports) else 1


if __name__ == "__main__":
    raise SystemExit(main())
