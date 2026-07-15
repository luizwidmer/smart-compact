#!/usr/bin/env python3
"""Install the Smart Compact skill, profile, plugin, and optional Spark agent."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence

if __package__:
    from .default_profile import ProfilePromotionError, promote_profile
    from .install_spark_agent import AppServerError, SPARK_MODEL, available_models
else:
    from default_profile import ProfilePromotionError, promote_profile
    from install_spark_agent import AppServerError, SPARK_MODEL, available_models


SOURCE_ROOT = Path(__file__).parents[1]
SKILL_NAME = "smart-compact"
PROFILE_FILENAME = "smart-compact.config.toml"
SUPPORTED_VERSIONS = ("v6", "v8")
OPTIMIZER_LANES = ("v8-natural",)
INSTALLABLE_VARIANTS = SUPPORTED_VERSIONS + OPTIMIZER_LANES
AGENT_FILENAME = "spark-worker.toml"
PLUGIN_NAME = "smart-compact"
MARKETPLACE_NAME = "personal"


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


def managed_file_state(
    content: str,
    target: Path,
    managed_contents: Iterable[str] = (),
) -> str:
    state = file_state(content, target)
    if state != "conflict" or not target.is_file():
        return state
    existing = target.read_text(encoding="utf-8")
    return "managed" if existing in managed_contents else state


def install_file(
    component: str,
    content: str,
    target: Path,
    *,
    mode: int,
    force: bool,
    dry_run: bool,
    managed_contents: Iterable[str] = (),
) -> InstallResult:
    state = managed_file_state(content, target, managed_contents)
    if state == "same":
        return InstallResult(component, "already-installed", target)
    if state == "conflict" and not force:
        return InstallResult(component, "conflict", target, "existing file differs")
    if dry_run:
        status = "would-update" if state == "conflict" else "would-install"
        return InstallResult(component, status, target)
    atomic_write(content, target, mode)
    status = "updated" if state in {"conflict", "managed"} else "installed"
    return InstallResult(component, status, target)


def skill_contents(source: Path) -> dict[Path, str]:
    return {
        Path("SKILL.md"): (source / "SKILL.md").read_text(encoding="utf-8"),
        Path("agents/openai.yaml"): (source / "agents" / "openai.yaml").read_text(
            encoding="utf-8"
        ),
    }


def compatibility_skill_contents(source_root: Path, version: str) -> dict[Path, str]:
    contents = skill_contents(source_root / "versions" / version)
    versioned_name = f"name: smart-compact-{version}"
    skill = contents[Path("SKILL.md")]
    if skill.count(versioned_name) != 1:
        raise ValueError(f"{version} skill must declare exactly one {versioned_name!r}")
    contents[Path("SKILL.md")] = skill.replace(versioned_name, "name: smart-compact", 1)
    agent = contents[Path("agents/openai.yaml")]
    contents[Path("agents/openai.yaml")] = (
        agent.replace(f'$smart-compact-{version}', "$smart-compact")
        .replace(f'display_name: "Smart Compact {version}"', 'display_name: "Smart Compact"')
    )
    return contents


def install_content_tree(
    component: str,
    contents: Mapping[Path, str],
    target: Path,
    *,
    force: bool = False,
    dry_run: bool = False,
    managed_variants: Sequence[Mapping[Path, str]] = (),
) -> InstallResult:
    states = {
        relative: managed_file_state(
            content,
            target / relative,
            (
                variant[relative]
                for variant in managed_variants
                if relative in variant
            ),
        )
        for relative, content in contents.items()
    }
    conflicts = [str(relative) for relative, state in states.items() if state == "conflict"]
    if conflicts and not force:
        return InstallResult(
            component,
            "conflict",
            target,
            "existing files differ: " + ", ".join(conflicts),
        )
    if all(state == "same" for state in states.values()):
        return InstallResult(component, "already-installed", target)
    if dry_run:
        status = "would-update" if target.exists() else "would-install"
        return InstallResult(component, status, target)

    for relative, content in contents.items():
        if states[relative] != "same":
            atomic_write(content, target / relative, 0o644)
    status = "updated" if target.exists() and any(
        state in {"conflict", "managed"} for state in states.values()
    ) else "installed"
    return InstallResult(component, status, target)


def install_tree(
    component: str,
    source: Path,
    target: Path,
    *,
    force: bool,
    dry_run: bool,
    overlays: Mapping[Path, str] | None = None,
    managed_overlays: Sequence[Mapping[Path, str]] = (),
) -> InstallResult:
    files = sorted(path for path in source.rglob("*") if path.is_file())
    if not files:
        return InstallResult(component, "conflict", target, "source tree is empty")
    base_contents = {
        path.relative_to(source): path.read_text(encoding="utf-8") for path in files
    }
    contents = dict(base_contents)
    if overlays:
        contents.update(overlays)
    states = {
        relative: managed_file_state(
            content,
            target / relative,
            (
                candidate
                for candidate in (
                    base_contents.get(relative),
                    *(overlay.get(relative) for overlay in managed_overlays),
                )
                if candidate is not None
            ),
        )
        for relative, content in contents.items()
    }
    conflicts = [str(relative) for relative, state in states.items() if state == "conflict"]
    if conflicts and not force:
        return InstallResult(
            component,
            "conflict",
            target,
            "existing files differ: " + ", ".join(conflicts),
        )
    if all(state == "same" for state in states.values()):
        return InstallResult(component, "already-installed", target)
    if dry_run:
        return InstallResult(component, "would-update" if target.exists() else "would-install", target)

    for relative, state in states.items():
        if state == "same":
            continue
        source_file = source / relative
        atomic_write(
            contents[relative],
            target / relative,
            source_file.stat().st_mode & 0o777 if source_file.is_file() else 0o644,
        )
    updated = any(state in {"conflict", "managed"} for state in states.values())
    return InstallResult(component, "updated" if updated else "installed", target)


def profile_contents(source_root: Path) -> dict[str, str]:
    return {
        version: (
            source_root / "profiles" / f"smart-compact-{version}.config.toml"
        ).read_text(encoding="utf-8")
        for version in INSTALLABLE_VARIANTS
    }


def plugin_alias_overlays(source_root: Path, version: str) -> dict[Path, str]:
    selected_skill = compatibility_skill_contents(source_root, version)
    return {
        Path("skills/smart-compact") / relative: content
        for relative, content in selected_skill.items()
    } | {
        Path("profiles/smart-compact.config.json"): (
            source_root
            / "plugin"
            / "profiles"
            / f"smart-compact-{version}.config.json"
        ).read_text(encoding="utf-8")
    }


def marketplace_entry() -> dict[str, object]:
    return {
        "name": PLUGIN_NAME,
        "source": {"source": "local", "path": f"./plugins/{PLUGIN_NAME}"},
        "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
        "category": "Productivity",
    }


def install_marketplace(
    target: Path,
    *,
    force: bool,
    dry_run: bool,
) -> InstallResult:
    if target.exists() and not target.is_file():
        return InstallResult(
            "plugin-marketplace", "conflict", target, "target is not a file"
        )

    if target.is_file():
        try:
            payload = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            return InstallResult(
                "plugin-marketplace", "conflict", target, f"invalid JSON: {error}"
            )
        if not isinstance(payload, dict) or not isinstance(payload.get("plugins"), list):
            return InstallResult(
                "plugin-marketplace",
                "conflict",
                target,
                "marketplace must be an object with a plugins array",
            )
    else:
        payload = {
            "name": MARKETPLACE_NAME,
            "interface": {"displayName": "Personal"},
            "plugins": [],
        }

    expected = marketplace_entry()
    plugins = payload["plugins"]
    existing_index = next(
        (
            index
            for index, entry in enumerate(plugins)
            if isinstance(entry, dict) and entry.get("name") == PLUGIN_NAME
        ),
        None,
    )
    if existing_index is not None and plugins[existing_index] == expected:
        return InstallResult("plugin-marketplace", "already-installed", target)
    if existing_index is not None and not force:
        return InstallResult(
            "plugin-marketplace",
            "conflict",
            target,
            "existing Smart Compact marketplace entry differs",
        )

    if existing_index is None:
        plugins.append(expected)
        action = "installed"
    else:
        plugins[existing_index] = expected
        action = "updated"
    if dry_run:
        return InstallResult(
            "plugin-marketplace",
            "would-update" if target.exists() else "would-install",
            target,
        )

    mode = target.stat().st_mode & 0o777 if target.exists() else 0o644
    atomic_write(json.dumps(payload, indent=2) + "\n", target, mode)
    return InstallResult("plugin-marketplace", action, target)


def activate_plugin(codex_name: str, personal_root: Path, timeout: float) -> InstallResult:
    codex = shutil.which(codex_name)
    if codex is None and Path(codex_name).is_file():
        codex = str(Path(codex_name).resolve())
    if codex is None:
        return InstallResult("plugin-activation", "skipped", None, "Codex CLI not found")

    try:
        marketplaces = subprocess.run(
            [codex, "plugin", "marketplace", "list"],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        if marketplaces.returncode != 0:
            detail = marketplaces.stderr.strip() or marketplaces.stdout.strip()
            return InstallResult("plugin-activation", "conflict", None, detail)
        configured = any(
            line.split(maxsplit=1)[0] == MARKETPLACE_NAME
            for line in marketplaces.stdout.splitlines()
            if line.strip() and not line.startswith("MARKETPLACE")
        )
        if not configured:
            added = subprocess.run(
                [codex, "plugin", "marketplace", "add", str(personal_root), "--json"],
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
            if added.returncode != 0:
                detail = added.stderr.strip() or added.stdout.strip()
                return InstallResult("plugin-activation", "conflict", None, detail)

        installed = subprocess.run(
            [codex, "plugin", "add", f"{PLUGIN_NAME}@{MARKETPLACE_NAME}", "--json"],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return InstallResult("plugin-activation", "conflict", None, str(error))

    if installed.returncode != 0:
        detail = installed.stderr.strip() or installed.stdout.strip()
        return InstallResult("plugin-activation", "conflict", None, detail)
    detail = installed.stdout.strip()
    return InstallResult("plugin-activation", "installed", None, detail)


def install_package(
    source_root: Path,
    skill_root: Path,
    codex_home: Path,
    *,
    version: str = "v8",
    force: bool = False,
    dry_run: bool = False,
    include_profile: bool = True,
    make_default: bool = False,
    include_plugin: bool = True,
    personal_root: Path | None = None,
    include_spark: bool = True,
    spark_available: bool = False,
    spark_detail: str = "",
) -> list[InstallResult]:
    if version not in SUPPORTED_VERSIONS:
        raise ValueError(
            f"unsupported Smart Compact version {version!r}; "
            f"expected one of {', '.join(SUPPORTED_VERSIONS)}"
        )
    if personal_root is None:
        personal_root = skill_root.parent.parent
    versioned_skills = {
        candidate: skill_contents(source_root / "versions" / candidate)
        for candidate in INSTALLABLE_VARIANTS
    }
    compatibility_skills = {
        candidate: compatibility_skill_contents(source_root, candidate)
        for candidate in SUPPORTED_VERSIONS
    }
    profiles = profile_contents(source_root)
    results = [
        install_content_tree(
            f"skill-{candidate}",
            versioned_skills[candidate],
            skill_root / f"{SKILL_NAME}-{candidate}",
            force=force,
            dry_run=dry_run,
        )
        for candidate in INSTALLABLE_VARIANTS
    ]
    results.append(
        install_content_tree(
            "skill-alias",
            compatibility_skills[version],
            skill_root / SKILL_NAME,
            force=force,
            dry_run=dry_run,
            managed_variants=tuple(compatibility_skills.values()),
        )
    )

    if include_profile:
        for candidate in INSTALLABLE_VARIANTS:
            results.append(
                install_file(
                    f"profile-{candidate}",
                    profiles[candidate],
                    codex_home / f"smart-compact-{candidate}.config.toml",
                    mode=0o600,
                    force=force,
                    dry_run=dry_run,
                )
            )
        results.append(
            install_file(
                "profile-alias",
                profiles[version],
                codex_home / PROFILE_FILENAME,
                mode=0o600,
                force=force,
                dry_run=dry_run,
                managed_contents=profiles.values(),
            )
        )
    else:
        results.append(InstallResult("profiles", "skipped", None, "disabled by --no-profile"))

    if make_default:
        try:
            promotion = promote_profile(
                source_root / "profiles" / f"smart-compact-{version}.config.toml",
                codex_home / "config.toml",
                dry_run=dry_run,
            )
            results.append(
                InstallResult(
                    "default-profile",
                    promotion.status,
                    promotion.target,
                    promotion.detail,
                )
            )
        except (OSError, ProfilePromotionError) as error:
            results.append(
                InstallResult(
                    "default-profile",
                    "conflict",
                    codex_home / "config.toml",
                    str(error),
                )
            )

    if include_plugin:
        selected_plugin_overlay = plugin_alias_overlays(source_root, version)
        all_plugin_overlays = tuple(
            plugin_alias_overlays(source_root, candidate)
            for candidate in SUPPORTED_VERSIONS
        )
        results.append(
            install_tree(
                "plugin-source",
                source_root / "plugin",
                personal_root / "plugins" / PLUGIN_NAME,
                force=force,
                dry_run=dry_run,
                overlays=selected_plugin_overlay,
                managed_overlays=all_plugin_overlays,
            )
        )
        results.append(
            install_marketplace(
                personal_root / ".agents" / "plugins" / "marketplace.json",
                force=force,
                dry_run=dry_run,
            )
        )
    else:
        results.append(
            InstallResult("plugin-source", "skipped", None, "disabled by --no-plugin")
        )
        results.append(
            InstallResult("plugin-marketplace", "skipped", None, "disabled by --no-plugin")
        )

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
    parser.add_argument(
        "--version",
        choices=SUPPORTED_VERSIONS,
        default="v8",
        help="compatibility alias version (default: v8; both versions are installed)",
    )
    parser.add_argument("--force", action="store_true", help="replace differing managed files")
    parser.add_argument("--dry-run", action="store_true", help="report changes without writing")
    parser.add_argument("--no-profile", action="store_true", help="skip the Codex profile")
    parser.add_argument(
        "--make-default",
        action="store_true",
        help="promote Smart Compact settings into the shared Codex config",
    )
    parser.add_argument("--no-plugin", action="store_true", help="skip the Codex plugin")
    parser.add_argument(
        "--no-spark",
        action="store_true",
        help="skip Spark capability detection and agent install",
    )
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
    parser.add_argument(
        "--personal-root",
        type=Path,
        default=Path.home(),
        help="personal plugin marketplace root (default: home directory)",
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
        version=args.version,
        force=args.force,
        dry_run=args.dry_run,
        include_profile=not args.no_profile,
        make_default=args.make_default,
        include_plugin=not args.no_plugin,
        personal_root=args.personal_root.expanduser(),
        include_spark=not args.no_spark,
        spark_available=spark_available,
        spark_detail=spark_detail,
    )

    if (
        not args.dry_run
        and not args.no_plugin
        and not any(result.status == "conflict" for result in results)
    ):
        results.append(activate_plugin(args.codex, args.personal_root.expanduser(), args.timeout))

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
        print(
            f"Start a new Codex task, then invoke $smart-compact "
            f"(alias for $smart-compact-{args.version})."
        )
        if not args.no_profile:
            print(
                f"CLI profiles: codex --profile smart-compact "
                f"or codex --profile smart-compact-{args.version}; "
                "optimizer lane: codex --profile smart-compact-v8-natural"
            )
        if args.make_default:
            print("Default profile: Smart Compact settings are active in new CLI and app tasks")
        if not args.no_plugin:
            print("App picker: select @Smart Compact, then ask it to start a profiled task")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
