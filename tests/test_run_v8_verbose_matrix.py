from __future__ import annotations

import json
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from unittest import mock

from scripts import run_v8_verbose_matrix as matrix


class ArtifactFactory:
    def __init__(self, invocation: matrix.Invocation) -> None:
        self.invocation = invocation

    @staticmethod
    def _metadata(arm: str) -> dict[str, object]:
        routing = {
            matrix.V8_NO_SPARK: "none",
            matrix.V8_FORCED: "forced",
            matrix.V8_AUTO: "auto",
        }[arm]
        return {
            "profile_path": f"/repo/{matrix.VERBOSE_PROFILE_SUFFIX}",
            "profile_sha256": "a" * 64,
            "policy_path": f"/repo/{matrix.VERBOSE_POLICY_SUFFIX}",
            "policy_sha256": "b" * 64,
            "routing_mode": routing,
            "spark_enabled": arm != matrix.V8_NO_SPARK,
        }

    @staticmethod
    def _row(case_id: str, arm: str, protocol_pass: bool) -> dict[str, object]:
        row: dict[str, object] = {
            "case_id": case_id,
            "trial": 1,
            "arm": arm,
            "task_pass": True,
            "scope_ok": True,
            "acceptance_observed": True,
            "usage_complete": True,
            "parent_total_tokens": 1000,
            "parent_usage": {"totalTokens": 1000},
            "no_active_children": True,
            "turn_status": "completed",
            "protocol_pass": protocol_pass,
            "success": protocol_pass,
            "effective_expectation": {"spawned_workers": {"min": 1, "max": None}},
        }
        if arm == matrix.V8_NO_SPARK:
            row.update(
                actual_spawned_workers=0,
                child_total_tokens=0,
                child_thread_ids=[],
                child_roles={},
                spawn_records={},
                routing_mode="none",
            )
        else:
            origin = "harness_thread" if arm == matrix.V8_FORCED else "parent_agent"
            native = arm == matrix.V8_AUTO
            row.update(
                actual_spawned_workers=1,
                child_total_tokens=100,
                child_thread_ids=["child"],
                child_roles={"child": "spark_worker"},
                spawn_records={
                    "child": {
                        "role": "spark_worker",
                        "model": matrix.SPARK_MODEL,
                        "origin": origin,
                        "native_agent_role": native,
                    }
                },
                routing_mode="forced" if arm == matrix.V8_FORCED else "auto",
            )
        return row

    def payload(self, *, protocol_pass: bool) -> dict[str, object]:
        return {
            "schema_version": 3,
            "complete": True,
            "publication_status": {"matrix_complete": True},
            "arms": list(self.invocation.arms),
            "arm_metadata": {
                arm: self._metadata(arm) for arm in self.invocation.arms
            },
            "model": self.invocation.setting.model,
            "effort": self.invocation.setting.effort,
            "repetitions": 1,
            "seed": matrix.SEED,
            "wall_time_contended": True,
            "results": [
                self._row(case_id, arm, protocol_pass)
                for case_id in self.invocation.case_ids
                for arm in self.invocation.arms
            ],
        }


class FakeProcess:
    def __init__(self, returncode: int = 0, polls_before_exit: int | None = 1) -> None:
        self.returncode = returncode
        self.polls_before_exit = polls_before_exit
        self.done = False
        self.terminate_calls = 0
        self.kill_calls = 0
        self.wait_calls = 0

    def poll(self) -> int | None:
        if self.done:
            return self.returncode
        if self.polls_before_exit is None:
            return None
        if self.polls_before_exit > 0:
            self.polls_before_exit -= 1
            return None
        self.done = True
        return self.returncode

    def wait(self, timeout: float | None = None) -> int:
        self.wait_calls += 1
        self.done = True
        return self.returncode

    def terminate(self) -> None:
        self.terminate_calls += 1
        self.returncode = -15
        self.done = True

    def kill(self) -> None:
        self.kill_calls += 1
        self.returncode = -9
        self.done = True


class MatrixPlanTests(unittest.TestCase):
    def test_exact_42_cell_matrix(self) -> None:
        plan = matrix.build_matrix(Path("/tmp/verbose-results"))
        self.assertEqual(len(plan), 13)
        self.assertEqual(sum(item.cells for item in plan), 42)
        allocation = Counter(
            arm for item in plan for arm in item.arms for _ in item.case_ids
        )
        self.assertEqual(
            allocation,
            {
                matrix.V8_NO_SPARK: 21,
                matrix.V8_FORCED: 12,
                matrix.V8_AUTO: 9,
            },
        )

        anchors = [item for item in plan if len(item.case_ids) == 1]
        self.assertEqual(len(anchors), 12)
        self.assertTrue(all(item.jobs == 1 for item in anchors))
        self.assertEqual(
            {(item.case_ids[0], item.setting.slug) for item in anchors},
            {
                (case_id, setting.slug)
                for case_id in (
                    "legacy-calculator",
                    "legacy-relay-bench",
                    "monorepo-sdk-migration",
                )
                for setting in matrix.SETTINGS
            },
        )
        non_anchor = plan[-1]
        self.assertEqual(non_anchor.case_ids, matrix.NON_ANCHOR_CASES)
        self.assertEqual(non_anchor.arms, (matrix.V8_NO_SPARK, matrix.V8_AUTO))
        self.assertEqual(non_anchor.setting.slug, "luna-xhigh")
        self.assertEqual(non_anchor.cells, 18)
        self.assertEqual(non_anchor.jobs, 4)

    def test_commands_use_verbose_wrapper_and_fixed_treatment(self) -> None:
        for invocation in matrix.build_matrix(Path("/tmp/verbose-results")):
            command = invocation.command("python-test")
            self.assertEqual(command[:2], ["python-test", str(matrix.WRAPPER)])
            self.assertNotIn("--v8-profile", command)
            self.assertIn("--external-contention", command)
            self.assertEqual(command.count("--arm"), len(invocation.arms))
            self.assertLessEqual(invocation.jobs, matrix.MAX_CONCURRENT)
            self.assertEqual(command[command.index("--seed") + 1], str(matrix.SEED))


class ArtifactPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.invocation = matrix.build_matrix(Path(self.temp.name))[0]

    def _write(self, payload: dict[str, object]) -> None:
        self.invocation.output.parent.mkdir(parents=True, exist_ok=True)
        self.invocation.output.write_text(json.dumps(payload), encoding="utf-8")

    def test_exit_one_is_accepted_only_as_protocol_only_miss(self) -> None:
        payload = ArtifactFactory(self.invocation).payload(protocol_pass=False)
        payload["results"][0]["scope_ok"] = False  # type: ignore[index]
        payload["results"][0]["usage_complete"] = False  # type: ignore[index]
        self._write(payload)
        result = matrix.validate_artifact(self.invocation, 1)
        self.assertTrue(result.tolerated_protocol_exit)

    def test_exit_zero_requires_full_success(self) -> None:
        self._write(ArtifactFactory(self.invocation).payload(protocol_pass=True))
        result = matrix.validate_artifact(self.invocation, 0)
        self.assertFalse(result.tolerated_protocol_exit)

    def test_exit_one_rejects_hard_gate_and_treatment_failures(self) -> None:
        factory = ArtifactFactory(self.invocation)
        cases = []

        incomplete = factory.payload(protocol_pass=False)
        incomplete["complete"] = False
        cases.append(incomplete)

        wrong_task = factory.payload(protocol_pass=False)
        wrong_task["results"][0]["task_pass"] = False  # type: ignore[index]
        cases.append(wrong_task)

        wrong_treatment = factory.payload(protocol_pass=False)
        wrong_treatment["arm_metadata"][matrix.V8_NO_SPARK][  # type: ignore[index]
            "profile_path"
        ] = "/repo/profiles/smart-compact-v8.config.toml"
        cases.append(wrong_treatment)

        unexpected_child = factory.payload(protocol_pass=False)
        unexpected_child["results"][0]["actual_spawned_workers"] = 1  # type: ignore[index]
        cases.append(unexpected_child)

        for payload in cases:
            with self.subTest(payload=payload):
                self._write(payload)
                with self.assertRaises(matrix.MatrixFailure):
                    matrix.validate_artifact(self.invocation, 1)


class SchedulerTests(unittest.TestCase):
    def test_scheduler_caps_concurrency_never_retries_and_reaps_all(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            plan = matrix.build_matrix(Path(temp))
            processes: list[FakeProcess] = []
            active = 0
            peak = 0

            def popen(
                command: list[str], *, cwd: Path, start_new_session: bool
            ) -> FakeProcess:
                nonlocal active, peak
                self.assertEqual(cwd, matrix.ROOT)
                self.assertTrue(start_new_session)
                process = FakeProcess(polls_before_exit=1)
                original_poll = process.poll

                def poll() -> int | None:
                    nonlocal active
                    was_done = process.done
                    result = original_poll()
                    if not was_done and process.done:
                        active -= 1
                    return result

                process.poll = poll  # type: ignore[method-assign]
                active += 1
                peak = max(peak, active)
                processes.append(process)
                return process

            def accepted(invocation: matrix.Invocation, returncode: int) -> matrix.CompletedInvocation:
                return matrix.CompletedInvocation(invocation, returncode, False)

            with mock.patch.object(matrix, "validate_artifact", side_effect=accepted):
                completed = matrix.run_matrix(
                    plan,
                    max_concurrent=4,
                    poll_interval=0,
                    popen=popen,
                    sleep=lambda _: None,
                )

        self.assertEqual(len(completed), 13)
        self.assertEqual(len(processes), 13)
        self.assertLessEqual(peak, 4)
        self.assertEqual(len({item.invocation.name for item in completed}), 13)
        self.assertTrue(all(process.wait_calls == 1 for process in processes))

    def test_substantive_failure_terminates_and_reaps_siblings(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            plan = matrix.build_matrix(Path(temp))[:2]
            failed = FakeProcess(returncode=2, polls_before_exit=0)
            sibling = FakeProcess(polls_before_exit=None)
            processes = iter((failed, sibling))

            def popen(
                command: list[str], *, cwd: Path, start_new_session: bool
            ) -> FakeProcess:
                self.assertTrue(start_new_session)
                return next(processes)

            with mock.patch.object(
                matrix,
                "validate_artifact",
                side_effect=matrix.MatrixFailure("substantive"),
            ):
                with self.assertRaises(matrix.MatrixFailure):
                    matrix.run_matrix(
                        plan,
                        max_concurrent=2,
                        poll_interval=0,
                        popen=popen,
                        sleep=lambda _: None,
                    )

        self.assertEqual(failed.wait_calls, 1)
        self.assertEqual(sibling.terminate_calls, 1)
        self.assertEqual(sibling.wait_calls, 1)

    def test_cleanup_signals_real_process_group(self) -> None:
        process = FakeProcess(polls_before_exit=None)
        process.pid = 12345  # type: ignore[attr-defined]
        with mock.patch.object(matrix.os, "killpg") as killpg:
            matrix.terminate_and_reap([process])
        killpg.assert_called_once_with(12345, matrix.signal.SIGTERM)
        self.assertEqual(process.terminate_calls, 0)
        self.assertEqual(process.wait_calls, 1)

    def test_concurrency_above_four_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            matrix.run_matrix([], max_concurrent=5)


if __name__ == "__main__":
    unittest.main()
