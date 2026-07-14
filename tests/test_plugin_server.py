from __future__ import annotations

import json
import os
import queue
import subprocess
import sys
import tempfile
import threading
import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
SERVER = ROOT / "plugin" / "mcp" / "server.mjs"
PLUGIN_PROFILE = ROOT / "plugin" / "profiles" / "smart-compact.config.json"
NATIVE_PROFILE = ROOT / "profiles" / "smart-compact.config.toml"
SMART_COMPACT_LABEL = "Smart Compact (recommended)"


class McpProcess:
    def __init__(self, environment: dict[str, str], *, form: bool = True) -> None:
        self.process = subprocess.Popen(
            ["node", str(SERVER)],
            cwd=ROOT,
            env=environment,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        self.messages: queue.Queue[dict[str, object] | None] = queue.Queue()
        self.reader = threading.Thread(target=self._read, daemon=True)
        self.reader.start()
        capabilities = {"extensions": {"openai/form": {}}} if form else {}
        self.send(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-11-25",
                    "capabilities": capabilities,
                    "clientInfo": {"name": "test", "version": "1"},
                },
            }
        )
        initialized = self.receive()
        if initialized.get("id") != 1 or "result" not in initialized:
            raise AssertionError(f"MCP initialization failed: {initialized}")
        self.send({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def _read(self) -> None:
        assert self.process.stdout is not None
        for line in self.process.stdout:
            self.messages.put(json.loads(line))
        self.messages.put(None)

    def send(self, message: dict[str, object]) -> None:
        assert self.process.stdin is not None
        self.process.stdin.write(json.dumps(message) + "\n")
        self.process.stdin.flush()

    def receive(self, timeout: float = 5.0) -> dict[str, object]:
        try:
            message = self.messages.get(timeout=timeout)
        except queue.Empty as error:
            stderr = self.process.stderr.read() if self.process.poll() is not None else ""
            raise AssertionError(f"timed out waiting for MCP output: {stderr}") from error
        if message is None:
            stderr = self.process.stderr.read() if self.process.stderr is not None else ""
            raise AssertionError(f"MCP server exited early: {stderr}")
        return message

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
        self.reader.join(timeout=1)
        if self.process.stdout is not None:
            self.process.stdout.close()
        if self.process.stderr is not None:
            self.process.stderr.close()

    def __enter__(self) -> "McpProcess":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


def fake_codex(root: Path) -> tuple[Path, Path, Path, Path]:
    executable = root / "fake-codex"
    args_path = root / "args.json"
    thread_path = root / "thread.json"
    name_path = root / "name.json"
    executable.write_text(
        f"#!{sys.executable}\n"
        "import json, os, sys\n"
        "from pathlib import Path\n"
        "Path(os.environ['FAKE_CODEX_ARGS']).write_text(json.dumps(sys.argv[1:]))\n"
        "for raw in sys.stdin:\n"
        "    request = json.loads(raw)\n"
        "    if 'id' not in request:\n"
        "        continue\n"
        "    method = request.get('method')\n"
        "    if method == 'initialize':\n"
        "        result = {}\n"
        "    elif method == 'thread/start':\n"
        "        Path(os.environ['FAKE_CODEX_THREAD']).write_text(json.dumps(request['params']))\n"
        "        result = {'thread': {'id': 'thread-test'}}\n"
        "    elif method == 'thread/name/set':\n"
        "        Path(os.environ['FAKE_CODEX_NAME']).write_text(json.dumps(request['params']))\n"
        "        result = {}\n"
        "    else:\n"
        "        result = {}\n"
        "    print(json.dumps({'jsonrpc': '2.0', 'id': request['id'], 'result': result}), flush=True)\n",
        encoding="utf-8",
    )
    executable.chmod(0o755)
    return executable, args_path, thread_path, name_path


def environment(codex_home: Path, executable: Path | None = None) -> dict[str, str]:
    value = os.environ.copy()
    value["CODEX_HOME"] = str(codex_home)
    value["SMART_COMPACT_APP_SERVER_TIMEOUT_MS"] = "3000"
    if executable is not None:
        value["SMART_COMPACT_CODEX"] = str(executable)
        value["FAKE_CODEX_ARGS"] = str(executable.parent / "args.json")
        value["FAKE_CODEX_THREAD"] = str(executable.parent / "thread.json")
        value["FAKE_CODEX_NAME"] = str(executable.parent / "name.json")
    return value


class PluginServerTests(unittest.TestCase):
    def test_bundled_profile_matches_native_profile(self) -> None:
        native = tomllib.loads(NATIVE_PROFILE.read_text(encoding="utf-8"))
        bundled = json.loads(PLUGIN_PROFILE.read_text(encoding="utf-8"))
        self.assertEqual(bundled, native)

    def test_plugin_skill_matches_package_skill(self) -> None:
        self.assertEqual(
            (ROOT / "plugin" / "skills" / "smart-compact" / "SKILL.md").read_text(
                encoding="utf-8"
            ),
            (ROOT / "SKILL.md").read_text(encoding="utf-8"),
        )
        self.assertEqual(
            (
                ROOT
                / "plugin"
                / "skills"
                / "smart-compact"
                / "agents"
                / "openai.yaml"
            ).read_text(encoding="utf-8"),
            (ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8"),
        )

    def test_lists_bundled_named_and_default_profiles(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            codex_home = Path(directory) / ".codex"
            codex_home.mkdir()
            (codex_home / "zeta.config.toml").write_text("model = 'test'\n")
            with McpProcess(environment(codex_home)) as client:
                client.send(
                    {
                        "jsonrpc": "2.0",
                        "id": 2,
                        "method": "tools/call",
                        "params": {
                            "name": "smart_compact_list_profiles",
                            "arguments": {},
                        },
                    }
                )
                response = client.receive()
            profiles = response["result"]["structuredContent"]["profiles"]
            self.assertEqual(
                [profile["id"] for profile in profiles],
                ["smart-compact", "zeta", "__codex_default__"],
            )
            self.assertEqual(profiles[0]["source"], "bundled")

    def test_picker_creates_task_with_installed_named_profile(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            codex_home = root / ".codex"
            workspace = root / "workspace"
            codex_home.mkdir()
            workspace.mkdir()
            (codex_home / "smart-compact.config.toml").write_text("model = 'test'\n")
            executable, args_path, thread_path, name_path = fake_codex(root)
            with McpProcess(environment(codex_home, executable)) as client:
                client.send(
                    {
                        "jsonrpc": "2.0",
                        "id": 2,
                        "method": "tools/call",
                        "params": {
                            "name": "smart_compact_start_task",
                            "arguments": {
                                "workspacePath": str(workspace),
                                "taskName": "Profile test",
                            },
                        },
                    }
                )
                form = client.receive()
                self.assertEqual(form["method"], "openai/form")
                profile_schema = form["params"]["requestedSchema"]["properties"]["profile"]
                self.assertEqual(profile_schema["default"], SMART_COMPACT_LABEL)
                self.assertIn(SMART_COMPACT_LABEL, profile_schema["enum"])
                client.send(
                    {
                        "jsonrpc": "2.0",
                        "id": form["id"],
                        "result": {
                            "action": "accept",
                            "content": {"profile": SMART_COMPACT_LABEL},
                        },
                    }
                )
                response = client.receive()

            result = response["result"]["structuredContent"]
            self.assertEqual(result["status"], "created")
            self.assertEqual(result["profile"], "smart-compact")
            self.assertEqual(result["url"], "codex://threads/thread-test")
            self.assertEqual(
                json.loads(args_path.read_text()),
                ["--profile", "smart-compact", "app-server", "--listen", "stdio://"],
            )
            self.assertNotIn("config", json.loads(thread_path.read_text()))
            self.assertEqual(json.loads(name_path.read_text())["name"], "Profile test")

    def test_picker_uses_bundled_profile_when_named_profile_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            codex_home = root / ".codex"
            workspace = root / "workspace"
            codex_home.mkdir()
            workspace.mkdir()
            executable, args_path, thread_path, _ = fake_codex(root)
            with McpProcess(environment(codex_home, executable)) as client:
                client.send(
                    {
                        "jsonrpc": "2.0",
                        "id": 2,
                        "method": "tools/call",
                        "params": {
                            "name": "smart_compact_start_task",
                            "arguments": {"workspacePath": str(workspace)},
                        },
                    }
                )
                form = client.receive()
                client.send(
                    {
                        "jsonrpc": "2.0",
                        "id": form["id"],
                        "result": {
                            "action": "accept",
                            "content": {"profile": SMART_COMPACT_LABEL},
                        },
                    }
                )
                response = client.receive()

            self.assertEqual(response["result"]["structuredContent"]["profileSource"], "bundled")
            self.assertEqual(
                json.loads(args_path.read_text()),
                ["app-server", "--listen", "stdio://"],
            )
            params = json.loads(thread_path.read_text())
            self.assertEqual(params["config"], json.loads(PLUGIN_PROFILE.read_text()))

    def test_cancelling_picker_does_not_spawn_codex(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            codex_home = root / ".codex"
            workspace = root / "workspace"
            codex_home.mkdir()
            workspace.mkdir()
            with McpProcess(environment(codex_home)) as client:
                client.send(
                    {
                        "jsonrpc": "2.0",
                        "id": 2,
                        "method": "tools/call",
                        "params": {
                            "name": "smart_compact_start_task",
                            "arguments": {"workspacePath": str(workspace)},
                        },
                    }
                )
                form = client.receive()
                client.send(
                    {
                        "jsonrpc": "2.0",
                        "id": form["id"],
                        "result": {"action": "cancel"},
                    }
                )
                response = client.receive()
            self.assertEqual(response["result"]["structuredContent"]["status"], "cancelled")


if __name__ == "__main__":
    unittest.main()
