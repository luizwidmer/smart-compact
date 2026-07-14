#!/usr/bin/env python3
"""Promote Smart Compact profile settings into Codex's base config safely."""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import stat
import tempfile
import tomllib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


MANAGED_TOP_LEVEL_KEYS = (
    "model_verbosity",
    "model_reasoning_summary",
    "tool_output_token_limit",
    "developer_instructions",
    "compact_prompt",
)
MANAGED_AGENT_KEYS = ("interrupt_message",)
TOP_BEGIN = "# BEGIN SMART COMPACT DEFAULTS"
TOP_END = "# END SMART COMPACT DEFAULTS"
AGENTS_BEGIN = "# BEGIN SMART COMPACT AGENT DEFAULTS"
AGENTS_END = "# END SMART COMPACT AGENT DEFAULTS"

_SECTION_RE = re.compile(r"^\s*\[([^\[\]]+)]\s*(?:#.*)?$")
_ASSIGNMENT_RE = re.compile(r"^\s*([A-Za-z0-9_-]+)\s*=")


class ProfilePromotionError(ValueError):
    """Raised when a profile cannot be promoted without risking the base config."""


@dataclass(frozen=True)
class AssignmentSpan:
    section: str | None
    key: str
    start: int
    end: int


@dataclass(frozen=True)
class PromotionResult:
    status: str
    target: Path
    backup: Path | None = None
    detail: str = ""


def _parse_toml(text: str, label: str) -> dict[str, object]:
    try:
        value = tomllib.loads(text)
    except tomllib.TOMLDecodeError as error:
        raise ProfilePromotionError(f"invalid {label}: {error}") from error
    if not isinstance(value, dict):
        raise ProfilePromotionError(f"invalid {label}: expected a TOML document")
    return value


def _assignment_end(lines: list[str], start: int) -> int:
    line = lines[start]
    separator = line.find("=")
    value = line[separator + 1 :] if separator >= 0 else ""
    for delimiter in ('"""', "'''"):
        opening = value.find(delimiter)
        if opening < 0:
            continue
        if value.find(delimiter, opening + 3) >= 0:
            return start + 1
        for index in range(start + 1, len(lines)):
            if delimiter in lines[index]:
                return index + 1
        raise ProfilePromotionError(
            f"unterminated multiline value beginning on line {start + 1}"
        )
    return start + 1


def _scan_assignments(lines: list[str]) -> list[AssignmentSpan]:
    spans: list[AssignmentSpan] = []
    section: str | None = None
    index = 0
    while index < len(lines):
        section_match = _SECTION_RE.match(lines[index])
        if section_match:
            section = section_match.group(1).strip()
            index += 1
            continue
        assignment_match = _ASSIGNMENT_RE.match(lines[index])
        if assignment_match:
            end = _assignment_end(lines, index)
            spans.append(
                AssignmentSpan(
                    section=section,
                    key=assignment_match.group(1),
                    start=index,
                    end=end,
                )
            )
            index = end
            continue
        index += 1
    return spans


def _remove_marker_block(lines: list[str], begin: str, end: str) -> list[str]:
    beginnings = [index for index, line in enumerate(lines) if line.strip() == begin]
    endings = [index for index, line in enumerate(lines) if line.strip() == end]
    if not beginnings and not endings:
        return lines
    if len(beginnings) != 1 or len(endings) != 1 or endings[0] < beginnings[0]:
        raise ProfilePromotionError(f"invalid managed marker pair {begin} / {end}")
    start, finish = beginnings[0], endings[0] + 1
    output = lines[:start] + lines[finish:]
    if start < len(output) and not output[start].strip():
        del output[start]
    if start > 0 and start - 1 < len(output) and not output[start - 1].strip():
        del output[start - 1]
    return output


def _extract_assignments(
    text: str,
    section: str | None,
    keys: tuple[str, ...],
) -> dict[str, str]:
    lines = text.splitlines(keepends=True)
    matches: dict[str, str] = {}
    for span in _scan_assignments(lines):
        if span.section == section and span.key in keys:
            if span.key in matches:
                raise ProfilePromotionError(
                    f"profile contains duplicate managed key {span.key!r}"
                )
            matches[span.key] = "".join(lines[span.start : span.end]).rstrip("\n")
    missing = [key for key in keys if key not in matches]
    if missing:
        location = "top level" if section is None else f"[{section}]"
        raise ProfilePromotionError(
            f"profile is missing managed keys in {location}: {', '.join(missing)}"
        )
    return matches


def _remove_managed_assignments(lines: list[str]) -> list[str]:
    spans = [
        span
        for span in _scan_assignments(lines)
        if (
            span.section is None
            and span.key in MANAGED_TOP_LEVEL_KEYS
            or span.section == "agents"
            and span.key in MANAGED_AGENT_KEYS
        )
    ]
    output = list(lines)
    for span in reversed(spans):
        del output[span.start : span.end]
    return output


def _managed_block(begin: str, assignments: dict[str, str], end: str) -> list[str]:
    block = [begin + "\n"]
    for value in assignments.values():
        block.extend((value + "\n").splitlines(keepends=True))
    block.append(end + "\n")
    return block


def _ensure_blank_before(lines: list[str], index: int) -> int:
    if index > 0 and lines[index - 1].strip():
        lines.insert(index, "\n")
        return index + 1
    return index


def _ensure_blank_after(lines: list[str], index: int) -> None:
    if index < len(lines) and lines[index].strip():
        lines.insert(index, "\n")


def render_promoted_config(profile_text: str, base_text: str) -> str:
    """Return base TOML with only Smart Compact-managed settings promoted."""

    profile = _parse_toml(profile_text, "Smart Compact profile")
    _parse_toml(base_text, "Codex base config")
    top_assignments = _extract_assignments(
        profile_text, None, MANAGED_TOP_LEVEL_KEYS
    )
    agent_assignments = _extract_assignments(
        profile_text, "agents", MANAGED_AGENT_KEYS
    )

    lines = base_text.splitlines(keepends=True)
    lines = _remove_marker_block(lines, TOP_BEGIN, TOP_END)
    lines = _remove_marker_block(lines, AGENTS_BEGIN, AGENTS_END)
    lines = _remove_managed_assignments(lines)
    while lines and not lines[0].strip():
        del lines[0]

    first_table = next(
        (index for index, line in enumerate(lines) if _SECTION_RE.match(line)),
        len(lines),
    )
    top_block = _managed_block(TOP_BEGIN, top_assignments, TOP_END)
    first_table = _ensure_blank_before(lines, first_table)
    lines[first_table:first_table] = top_block
    after_top = first_table + len(top_block)
    _ensure_blank_after(lines, after_top)

    agents_header = next(
        (
            index
            for index, line in enumerate(lines)
            if (match := _SECTION_RE.match(line))
            and match.group(1).strip() == "agents"
        ),
        None,
    )
    agents_block = _managed_block(AGENTS_BEGIN, agent_assignments, AGENTS_END)
    if agents_header is None:
        if lines and lines[-1].strip():
            lines.append("\n")
        lines.append("[agents]\n")
        lines.extend(agents_block)
    else:
        insertion = agents_header + 1
        lines[insertion:insertion] = agents_block

    rendered = "".join(lines)
    if rendered and not rendered.endswith("\n"):
        rendered += "\n"
    result = _parse_toml(rendered, "promoted Codex base config")
    for key in MANAGED_TOP_LEVEL_KEYS:
        if result.get(key) != profile.get(key):
            raise ProfilePromotionError(f"promotion verification failed for {key!r}")
    result_agents = result.get("agents")
    profile_agents = profile.get("agents")
    if not isinstance(result_agents, dict) or not isinstance(profile_agents, dict):
        raise ProfilePromotionError("promotion verification failed for [agents]")
    for key in MANAGED_AGENT_KEYS:
        if result_agents.get(key) != profile_agents.get(key):
            raise ProfilePromotionError(f"promotion verification failed for agents.{key}")
    return rendered


def _atomic_write(content: str, target: Path, mode: int) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{target.name}-", suffix=".tmp", dir=target.parent, text=True
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(content)
        os.chmod(temporary, mode)
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)


def _backup_config(config_path: Path, backup_root: Path) -> Path:
    content = config_path.read_bytes()
    digest = hashlib.sha256(content).hexdigest()[:12]
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup = backup_root / f"config.toml.{timestamp}.{digest}.bak"
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(config_path, backup)
    if backup.read_bytes() != content:
        backup.unlink(missing_ok=True)
        raise OSError("base config backup verification failed")
    return backup


def promote_profile(
    profile_path: Path,
    config_path: Path,
    *,
    dry_run: bool = False,
    backup_root: Path | None = None,
) -> PromotionResult:
    profile_text = profile_path.read_text(encoding="utf-8")
    existed = config_path.exists()
    base_text = config_path.read_text(encoding="utf-8") if existed else ""
    rendered = render_promoted_config(profile_text, base_text)
    if rendered == base_text:
        return PromotionResult("already-installed", config_path)
    status = "would-update" if existed else "would-install"
    if dry_run:
        return PromotionResult(status, config_path)

    backup: Path | None = None
    mode = 0o600
    if existed:
        mode = stat.S_IMODE(config_path.stat().st_mode)
        root = backup_root or config_path.parent / "backups" / "smart-compact"
        backup = _backup_config(config_path, root)
    _atomic_write(rendered, config_path, mode)
    detail = f"backup: {backup}" if backup is not None else "created new base config"
    return PromotionResult("updated" if existed else "installed", config_path, backup, detail)
