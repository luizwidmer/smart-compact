from __future__ import annotations

import unittest

from scripts.benchmark_spark_spawn import (
    DEFAULT_PROMPT,
    benchmark_ok,
    spawn_record,
    started_subagent_ids,
)


class SparkSpawnBenchmarkTests(unittest.TestCase):
    def test_default_prompt_explicitly_prioritizes_parent_allowance(self) -> None:
        self.assertIn("explicit optimization goal", DEFAULT_PROMPT)
        self.assertIn("preserve the parent-model allowance", DEFAULT_PROMPT)
        self.assertIn("six exclusive files", DEFAULT_PROMPT)

    def test_extracts_spawn_item(self) -> None:
        notification = {
            "method": "item/completed",
            "params": {
                "item": {
                    "type": "collabAgentToolCall",
                    "tool": "spawnAgent",
                    "id": "call-1",
                    "model": "gpt-5.3-codex-spark",
                    "status": "completed",
                    "receiverThreadIds": ["thread-1"],
                }
            },
        }
        self.assertEqual(
            spawn_record(notification),
            {
                "id": "call-1",
                "model": "gpt-5.3-codex-spark",
                "status": "completed",
                "receiver_thread_ids": ["thread-1"],
            },
        )

    def test_ignores_non_spawn_items(self) -> None:
        notification = {
            "method": "item/completed",
            "params": {"item": {"type": "commandExecution", "id": "call-2"}},
        }
        self.assertIsNone(spawn_record(notification))

    def test_counts_only_started_child_threads(self) -> None:
        activities = [
            {"agent_thread_id": "child", "agent_path": "/root/spark_worker", "kind": "started"},
            {"agent_thread_id": "parent", "agent_path": "/root", "kind": "interacted"},
        ]
        self.assertEqual(started_subagent_ids(activities, "parent"), ["child"])

    def test_requires_completed_turn_and_exactly_one_spark_child(self) -> None:
        passing = {
            "turn_status": "completed",
            "spark_spawned": True,
            "spawn_count": 1,
            "final_message": "done",
        }
        self.assertTrue(benchmark_ok(passing))
        for key, value in (
            ("turn_status", "failed"),
            ("spark_spawned", False),
            ("spawn_count", 2),
            ("final_message", None),
        ):
            with self.subTest(key=key):
                candidate = dict(passing)
                candidate[key] = value
                self.assertFalse(benchmark_ok(candidate))


if __name__ == "__main__":
    unittest.main()
