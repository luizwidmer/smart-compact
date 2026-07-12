#!/usr/bin/env python3
"""Install the optional Spark custom agent only when the local model catalog exposes it."""

from __future__ import annotations

import argparse
import json
import os
import queue
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path
from typing import TextIO


SPARK_MODEL = "gpt-5.3-codex-spark"
AGENT_FILENAME = "spark-worker.toml"
TEMPLATE = Path(__file__).parents[1] / ".codex" / "agents" / AGENT_FILENAME


class AppServerError(RuntimeError):
    """Raised when the local Codex app-server cannot answer a catalog request."""


class AppServerClient:
    def __init__(self, codex: str, timeout: float) -> None:
        self.timeout = timeout
        self.process = subprocess.Popen(
            [codex, "app-server", "--listen", "stdio://"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            bufsize=1,
        )
        if self.process.stdin is None or self.process.stdout is None:
            raise AppServerError("failed to open app-server pipes")
        self.stdin: TextIO = self.process.stdin
        self.messages: queue.Queue[dict[str, object] | None] = queue.Queue()
        threading.Thread(target=self._read, args=(self.process.stdout,), daemon=True).start()

    def _read(self, stream: TextIO) -> None:
        for line in stream:
            try:
                message = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(message, dict):
                self.messages.put(message)
        self.messages.put(None)

    def send(self, payload: dict[str, object]) -> None:
        self.stdin.write(json.dumps(payload, separators=(",", ":")) + "\n")
        self.stdin.flush()

    def request(self, request_id: int, method: str, params: dict[str, object]) -> dict[str, object]:
        self.send({"id": request_id, "method": method, "params": params})
        while True:
            try:
                message = self.messages.get(timeout=self.timeout)
            except queue.Empty as error:
                raise AppServerError(f"timed out waiting for {method}") from error
            if message is None:
                raise AppServerError("app-server closed before replying")
            if message.get("id") != request_id:
                continue
            if "error" in message:
                raise AppServerError(f"{method} failed: {message['error']}")
            result = message.get("result")
            if not isinstance(result, dict):
                raise AppServerError(f"{method} returned an invalid result")
            return result

    def close(self) -> None:
        try:
            self.stdin.close()
        except OSError:
            pass
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=2)


def available_models(codex: str, timeout: float = 15.0) -> set[str]:
    client = AppServerClient(codex, timeout)
    try:
        client.request(
            1,
            "initialize",
            {"clientInfo": {"name": "smart-compact", "version": "1"}},
        )
        client.send({"method": "initialized"})
        models: set[str] = set()
        cursor: str | None = None
        request_id = 2
        while True:
            params: dict[str, object] = {"includeHidden": True, "limit": 100}
            if cursor is not None:
                params["cursor"] = cursor
            result = client.request(request_id, "model/list", params)
            data = result.get("data", [])
            if not isinstance(data, list):
                raise AppServerError("model/list returned invalid data")
            for item in data:
                if not isinstance(item, dict):
                    continue
                for key in ("id", "model"):
                    value = item.get(key)
                    if isinstance(value, str):
                        models.add(value)
            next_cursor = result.get("nextCursor")
            if not isinstance(next_cursor, str) or not next_cursor:
                return models
            cursor = next_cursor
            request_id += 1
    finally:
        client.close()


def install_agent(content: str, target: Path, force: bool = False) -> str:
    if target.exists():
        current = target.read_text(encoding="utf-8")
        if current == content:
            return "already-installed"
        if not force:
            return "conflict"

    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{target.stem}-",
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="report availability without installing")
    parser.add_argument("--force", action="store_true", help="replace a different existing agent file")
    parser.add_argument("--codex", default="codex", help="Codex CLI executable or path")
    parser.add_argument("--timeout", type=float, default=15.0, help="seconds per app-server response")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    codex = shutil.which(args.codex)
    if codex is None:
        print("Spark unavailable: Codex CLI not found. No changes made.")
        return 0

    try:
        models = available_models(codex, args.timeout)
    except (AppServerError, OSError) as error:
        print(f"Spark availability unknown: {error}. No changes made.")
        return 0

    if SPARK_MODEL not in models:
        print(f"Spark unavailable: {SPARK_MODEL} is not in the local model catalog. No changes made.")
        return 0

    print(f"Spark available: {SPARK_MODEL}.")
    if args.check:
        return 0

    codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
    target = codex_home / "agents" / AGENT_FILENAME
    status = install_agent(TEMPLATE.read_text(encoding="utf-8"), target, args.force)
    if status == "conflict":
        print(f"Existing agent differs: {target}. Re-run with --force to replace it.")
    elif status == "already-installed":
        print(f"Spark agent already installed: {target}")
    else:
        print(f"Installed Spark agent: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
