from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.rtk_trace_audit import audit_rollout, extract_exec_commands


def write_rollout(directory: str, payloads: list[dict[str, object]]) -> Path:
    path = Path(directory) / "rollout.jsonl"
    path.write_text(
        "\n".join(json.dumps({"type": "response_item", "payload": payload}) for payload in payloads)
        + "\n",
        encoding="utf-8",
    )
    return path


class RtkTraceAuditTests(unittest.TestCase):
    def test_extracts_multiple_literal_commands(self) -> None:
        source = (
            'await Promise.all([tools.exec_command({"cmd":"rtk cat a"}),'
            'tools.exec_command({cmd: "rtk rg x"})]);'
        )
        self.assertEqual(extract_exec_commands(source), ["rtk cat a", "rtk rg x"])

    def test_accepts_strict_rtk_trace(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = write_rollout(
                directory,
                [
                    {
                        "type": "custom_tool_call",
                        "name": "exec",
                        "input": 'await tools.exec_command({cmd:"rtk cat SPEC.md"});',
                    },
                    {
                        "type": "function_call",
                        "name": "exec_command",
                        "arguments": json.dumps({"cmd": "rtk python3 test.py"}),
                    },
                ],
            )
            report = audit_rollout(path)
        self.assertTrue(report["compliant"])
        self.assertEqual(report["rtk_calls"], 2)

    def test_rejects_direct_command(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = write_rollout(
                directory,
                [
                    {
                        "type": "custom_tool_call",
                        "name": "exec",
                        "input": 'await tools.exec_command({cmd:"python3 test.py"});',
                    }
                ],
            )
            report = audit_rollout(path)
        self.assertFalse(report["compliant"])
        self.assertEqual(report["violations"][0]["reason"], "command does not start with rtk")

    def test_rejects_dynamic_command_that_cannot_be_audited(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = write_rollout(
                directory,
                [
                    {
                        "type": "custom_tool_call",
                        "name": "exec",
                        "input": 'const cmd="rtk cat x"; await tools.exec_command({cmd});',
                    }
                ],
            )
            report = audit_rollout(path)
        self.assertFalse(report["compliant"])
        self.assertEqual(report["violations"][0]["reason"], "command is not a literal")


if __name__ == "__main__":
    unittest.main()
