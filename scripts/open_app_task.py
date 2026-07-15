#!/usr/bin/env python3
"""Create one Smart Compact-configured task and open it in the Codex app."""

from __future__ import annotations

import argparse
import json
import os
import queue
import shutil
import subprocess
import sys
import threading
import time
import tomllib
from collections import deque
from pathlib import Path
from typing import Any


PROFILE_FILENAME = "smart-compact.config.toml"
DEFAULT_APP_CODEX = Path("/Applications/ChatGPT.app/Contents/Resources/codex")


class AppTaskError(RuntimeError):
    """Raised when the local Codex app-server cannot create a configured task."""


def app_server_command(codex: str, config_overrides: list[str] | None = None) -> list[str]:
    override_args: list[str] = []
    for value in config_overrides or []:
        if value == "features.multi_agent=false":
            override_args.extend(("--disable", "multi_agent"))
        elif value == "features.multi_agent=true":
            override_args.extend(("--enable", "multi_agent"))
        else:
            override_args.extend(("-c", value))
    return [codex, *override_args, "app-server", "--listen", "stdio://"]


def default_codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser()


def default_profile_path() -> Path:
    installed = default_codex_home() / PROFILE_FILENAME
    checkout = Path(__file__).parents[1] / "profiles" / PROFILE_FILENAME
    return installed if installed.is_file() else checkout


def resolve_codex(requested: str | None) -> str:
    candidates = [requested, os.environ.get("CODEX_CLI_PATH"), shutil.which("codex")]
    candidates.append(str(DEFAULT_APP_CODEX) if DEFAULT_APP_CODEX.is_file() else None)
    for candidate in candidates:
        if not candidate:
            continue
        resolved = shutil.which(candidate) or candidate
        if Path(resolved).is_file():
            return str(Path(resolved).resolve())
    raise AppTaskError("Codex CLI not found; pass --codex /absolute/path/to/codex")


def load_profile(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise AppTaskError(f"Smart Compact profile not found: {path}")
    config = tomllib.loads(path.read_text(encoding="utf-8"))
    if not isinstance(config, dict) or not config:
        raise AppTaskError(f"Smart Compact profile is empty: {path}")
    try:
        json.dumps(config)
    except TypeError as error:
        raise AppTaskError(f"Profile contains a non-JSON value: {error}") from error
    return config


def thread_start_params(cwd: Path, config: dict[str, Any], *, ephemeral: bool = False) -> dict[str, Any]:
    return {
        "cwd": str(cwd),
        "ephemeral": ephemeral,
        "config": config,
    }


def task_url(thread_id: str) -> str:
    return f"codex://threads/{thread_id}"


class AppServerClient:
    def __init__(
        self,
        codex: str,
        timeout: float,
        config_overrides: list[str] | None = None,
        environment: dict[str, str] | None = None,
    ) -> None:
        self.timeout = timeout
        self.process = subprocess.Popen(
            app_server_command(codex, config_overrides),
            env={**os.environ, **(environment or {})},
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        self.messages: queue.Queue[dict[str, Any] | None] = queue.Queue()
        self.notifications: queue.Queue[dict[str, Any] | None] = queue.Queue()
        self.logs: deque[str] = deque(maxlen=8)
        self.reader = threading.Thread(target=self._read, daemon=True)
        self.reader.start()

    def _read(self) -> None:
        assert self.process.stdout is not None
        for raw_line in self.process.stdout:
            line = raw_line.strip()
            if not line:
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                self.logs.append(line)
                continue
            if isinstance(value, dict) and "id" in value:
                self.messages.put(value)
            elif isinstance(value, dict) and "method" in value:
                self.notifications.put(value)
            elif isinstance(value, dict) and "level" in value:
                self.logs.append(line)
        self.messages.put(None)
        self.notifications.put(None)

    def _send(self, message: dict[str, Any]) -> None:
        if self.process.stdin is None or self.process.poll() is not None:
            raise AppTaskError(self._failure("app-server exited before request"))
        self.process.stdin.write(json.dumps(message, separators=(",", ":")) + "\n")
        self.process.stdin.flush()

    def request(self, request_id: int, method: str, params: dict[str, Any]) -> dict[str, Any]:
        self._send({"method": method, "id": request_id, "params": params})
        deadline = time.monotonic() + self.timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise AppTaskError(self._failure(f"timed out waiting for {method}"))
            try:
                message = self.messages.get(timeout=remaining)
            except queue.Empty as error:
                raise AppTaskError(self._failure(f"timed out waiting for {method}")) from error
            if message is None:
                raise AppTaskError(self._failure(f"app-server closed while waiting for {method}"))
            if message.get("id") != request_id:
                continue
            if "error" in message:
                raise AppTaskError(f"{method} failed: {message['error']}")
            result = message.get("result")
            if not isinstance(result, dict):
                raise AppTaskError(f"{method} returned an invalid response")
            return result

    def notify(self, method: str, params: dict[str, Any] | None = None) -> None:
        self._send({"method": method, "params": params or {}})

    def next_notification(self, timeout: float) -> dict[str, Any]:
        try:
            message = self.notifications.get(timeout=timeout)
        except queue.Empty as error:
            raise AppTaskError(self._failure("timed out waiting for app-server notification")) from error
        if message is None:
            raise AppTaskError(self._failure("app-server closed while waiting for notification"))
        return message

    def initialize(self) -> None:
        self.request(
            0,
            "initialize",
            {
                "clientInfo": {
                    "name": "smart_compact",
                    "title": "Smart Compact",
                    "version": "0.1.0",
                }
            },
        )
        self.notify("initialized")

    def close(self) -> None:
        if self.process.stdin is not None and not self.process.stdin.closed:
            self.process.stdin.close()
        try:
            self.process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            self.process.terminate()
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=2)

    def _failure(self, message: str) -> str:
        detail = f"; recent output: {' | '.join(self.logs)}" if self.logs else ""
        return message + detail

    def __enter__(self) -> "AppServerClient":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


def create_task(
    codex: str,
    cwd: Path,
    config: dict[str, Any],
    name: str,
    timeout: float,
    *,
    ephemeral: bool = False,
) -> str:
    with AppServerClient(codex, timeout) as client:
        client.initialize()
        result = client.request(
            1,
            "thread/start",
            thread_start_params(cwd, config, ephemeral=ephemeral),
        )
        thread = result.get("thread")
        if not isinstance(thread, dict) or not isinstance(thread.get("id"), str):
            raise AppTaskError("thread/start did not return a thread id")
        thread_id = thread["id"]
        if name and not ephemeral:
            client.request(2, "thread/name/set", {"threadId": thread_id, "name": name})
        return thread_id


def open_task(url: str) -> None:
    if sys.platform == "darwin":
        command = ["open", url]
    elif os.name == "nt":
        os.startfile(url)  # type: ignore[attr-defined]
        return
    else:
        command = ["xdg-open", url]
    try:
        subprocess.run(command, check=True)
    except (OSError, subprocess.CalledProcessError) as error:
        raise AppTaskError(f"Task was created but the app could not be opened: {url}") from error


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", type=Path, default=Path.cwd(), help="workspace path")
    parser.add_argument("--profile", type=Path, default=None, help="profile TOML path")
    parser.add_argument("--codex", default=None, help="Codex CLI executable or path")
    parser.add_argument("--name", default=None, help="task name shown in the app")
    parser.add_argument("--timeout", type=float, default=20.0, help="seconds per app-server response")
    parser.add_argument("--no-open", action="store_true", help="create the task without opening the app")
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate with an ephemeral task and do not open the app",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    cwd = args.path.expanduser().resolve()
    if not cwd.is_dir():
        print(f"Workspace is not a directory: {cwd}", file=sys.stderr)
        return 2
    profile = (args.profile or default_profile_path()).expanduser().resolve()
    name = args.name or f"Smart Compact - {cwd.name}"
    try:
        thread_id = create_task(
            resolve_codex(args.codex),
            cwd,
            load_profile(profile),
            name,
            args.timeout,
            ephemeral=args.check,
        )
        url = task_url(thread_id)
        if not args.no_open and not args.check:
            open_task(url)
    except AppTaskError as error:
        print(f"smart-compact-app: {error}", file=sys.stderr)
        return 1
    if args.check:
        print(f"Smart Compact app profile check passed ({thread_id})")
    else:
        print(f"Created Smart Compact task {thread_id}")
        print(url)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
