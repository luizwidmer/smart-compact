#!/usr/bin/env python3
"""Install the optional Smart Compact Codex profile without overwriting by default."""

from __future__ import annotations

import argparse
import os
import tempfile
from pathlib import Path


SOURCE = Path(__file__).parents[1] / "profiles" / "smart-compact.config.toml"


def install_profile(content: str, target: Path, force: bool = False) -> str:
    if target.exists():
        current = target.read_text(encoding="utf-8")
        if current == content:
            return "already-installed"
        if not force:
            return "conflict"

    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".smart-compact-",
        suffix=".tmp",
        dir=target.parent,
        text=True,
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(content)
        os.chmod(temporary, 0o600)
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
    return "installed"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="replace a different existing profile")
    args = parser.parse_args()

    codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
    target = codex_home / "smart-compact.config.toml"
    status = install_profile(SOURCE.read_text(encoding="utf-8"), target, args.force)
    if status == "conflict":
        print(f"Existing profile differs: {target}. Re-run with --force to replace it.")
    elif status == "already-installed":
        print(f"Smart Compact profile already installed: {target}")
    else:
        print(f"Installed Smart Compact profile: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
