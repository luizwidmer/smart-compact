#!/usr/bin/env python3
"""Install the Smart Compact skill, profile, and capability-gated Spark agent."""

from __future__ import annotations

import argparse
import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

if __package__:
    from .install_spark_agent import AppServerError, SPARK_MODEL, available_models
else:
    from install_spark_agent import AppServerError, SPARK_MODEL, available_models


SOURCE_ROOT = Path(__file__).parents[1]
SKILL_NAME = "codex-compact"
PROFILE_FILENAME = "smart-compact.config.toml"
AGENT_FILENAME = "spark-worker.toml"


@dataclass(frozen=True)
class InstallResult:
    component: str
    status: str
    target: Path | None
    detail: str = ""


def atomic_write(content: str, target: Path, mode: int) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{target.name}-",
        suffix=".tmp",
        dir=target.parent,
        text=True,
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(content)
        os.chmod(temporary, mode)
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)


def file_state(content: str, target: Path) -> str:
    if not target.exists():
        return "missing"
    if not target.is_file():
        return "conflict"
    return "same" if target.read_text(encoding="utf-8") == content else "conflict"


def install_file(
    component: str,
    content: str,
    target: Path,
    *,
    mode: int,
    force: bool,
    dry_run: bool,
) -> InstallResult:
    state = file_state(content, target)
    if state == "same":
        return InstallResult(component, "already-installed", target)
    if state == "conflict" and not force:
        return InstallResult(component, "conflict", target, "existing file differs")
    if dry_run:
        status = "would-update" if state == "conflict" else "would-install"
        return InstallResult(component, status, target)
    atomic_write(content, target, mode)
    status = "updated" if state == "conflict" else "installed"
    return InstallResult(component, status, target)


def install_skill(
    source_root: Path,
    target: Path,
    *,
    force: bool = False,
    dry_run: bool = False,
) -> InstallResult:
    files = {
        Path("SKILL.md"): source_root / "SKILL.md",
        Path("agents/openai.yaml"): source_root / "agents" / "openai.yaml",
    }
    states = {
        relative: file_state(source.read_text(encoding="utf-8"), target / relative)
        for relative, source in files.items()
    }
    conflicts = [str(relative) for relative, state in states.items() if state == "conflict"]
    if conflicts and not force:
        return InstallResult(
            "skill",
            "conflict",
            target,
            "existing files differ: " + ", ".join(conflicts),
        )
    if all(state == "same" for state in states.values()):
        return InstallResult("skill", "already-installed", target)
    if dry_run:
        status = "would-update" if conflicts else "would-install"
        return InstallResult("skill", status, target)

    for relative, source in files.items():
        content = source.read_text(encoding="utf-8")
        if states[relative] != "same":
            atomic_write(content, target / relative, 0o644)
    status = "updated" if conflicts else "installed"
    return InstallResult("skill", status, target)


def install_package(
    source_root: Path,
    skill_root: Path,
    codex_home: Path,
    *,
    force: bool = False,
    dry_run: bool = False,
    include_profile: bool = True,
    include_spark: bool = True,
    spark_available: bool = False,
    spark_detail: str = "",
) -> list[InstallResult]:
    results = [
        install_skill(
            source_root,
            skill_root / SKILL_NAME,
            force=force,
            dry_run=dry_run,
        )
    ]

    if include_profile:
        results.append(
            install_file(
                "profile",
                (source_root / "profiles" / PROFILE_FILENAME).read_text(encoding="utf-8"),
                codex_home / PROFILE_FILENAME,
                mode=0o600,
                force=force,
                dry_run=dry_run,
            )
        )
    else:
        results.append(InstallResult("profile", "skipped", None, "disabled by --no-profile"))

    if not include_spark:
        results.append(InstallResult("spark-agent", "skipped", None, "disabled by --no-spark"))
    elif not spark_available:
        results.append(InstallResult("spark-agent", "skipped", None, spark_detail))
    else:
        results.append(
            install_file(
                "spark-agent",
                (source_root / ".codex" / "agents" / AGENT_FILENAME).read_text(encoding="utf-8"),
                codex_home / "agents" / AGENT_FILENAME,
                mode=0o600,
                force=force,
                dry_run=dry_run,
            )
        )
    return results


def spark_capability(codex_name: str, timeout: float) -> tuple[bool, str]:
    codex = shutil.which(codex_name)
    if codex is None:
        return False, "Codex CLI not found"
    try:
        models = available_models(codex, timeout)
    except (AppServerError, OSError) as error:
        return False, f"availability unknown: {error}"
    if SPARK_MODEL not in models:
        return False, f"{SPARK_MODEL} is not in the local model catalog"
    return True, f"{SPARK_MODEL} is available"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="replace differing managed files")
    parser.add_argument("--dry-run", action="store_true", help="report changes without writing")
    parser.add_argument("--no-profile", action="store_true", help="skip the Codex profile")
    parser.add_argument("--no-spark", action="store_true", help="skip Spark capability detection and agent install")
    parser.add_argument("--codex", default="codex", help="Codex CLI executable or path")
    parser.add_argument("--timeout", type=float, default=15.0, help="seconds per app-server response")
    parser.add_argument(
        "--skill-root",
        type=Path,
        default=Path.home() / ".agents" / "skills",
        help="global skills directory (default: ~/.agents/skills)",
    )
    parser.add_argument(
        "--codex-home",
        type=Path,
        default=Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")),
        help="Codex home directory (default: CODEX_HOME or ~/.codex)",
    )
    return parser


def render_result(result: InstallResult) -> str:
    location = f" -> {result.target}" if result.target is not None else ""
    detail = f" ({result.detail})" if result.detail else ""
    return f"[{result.status}] {result.component}{location}{detail}"


def main() -> int:
    args = build_parser().parse_args()
    spark_available = False
    spark_detail = ""
    if not args.no_spark:
        spark_available, spark_detail = spark_capability(args.codex, args.timeout)

    results = install_package(
        SOURCE_ROOT,
        args.skill_root.expanduser(),
        args.codex_home.expanduser(),
        force=args.force,
        dry_run=args.dry_run,
        include_profile=not args.no_profile,
        include_spark=not args.no_spark,
        spark_available=spark_available,
        spark_detail=spark_detail,
    )

    print("Smart Compact installation plan:" if args.dry_run else "Smart Compact installation:")
    for result in results:
        print(f"  {render_result(result)}")

    rtk = shutil.which("rtk")
    if rtk:
        print(f"  [detected] RTK -> {rtk}")
    else:
        print("  [optional] RTK not found; Smart Compact still works without it")

    if any(result.status == "conflict" for result in results):
        print("No conflicting component was overwritten. Re-run with --force to update it.")
        return 1
    if args.dry_run:
        print("Dry run complete; no files were changed.")
    else:
        print("Start a new Codex task, then invoke $codex-compact.")
        if not args.no_profile:
            print("CLI profile: codex --profile smart-compact")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
