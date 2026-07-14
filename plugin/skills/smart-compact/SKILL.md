---
name: smart-compact
description: Reduce Codex communication and context usage while preserving correctness and safety. Use for token-efficient implementation work, concise responses, progress updates, summaries, and subagent handoffs.
---

# Smart Compact

Minimize context consumption without changing required scope or correctness.

## Communicate compactly

- Lead with the outcome. Keep decisive evidence, material risk, blockers, and a useful next action.
- Remove repetition, pleasantries, process diaries, decorative structure, and obvious transitions.
- Preserve code, commands, paths, identifiers, numbers, units, negation, conditions, uncertainty, and action order exactly.
- Use complete sentences when fragments could be ambiguous.

## Work economically

Do not add planning, inspection, testing, or narration solely because this skill is active.

For a bounded local task with a complete specification, one owner, an exact target root, and a supplied acceptance command:

1. Do not create a plan or reread instructions already in context.
2. Read only the specification and target state needed to implement. Do not inspect sibling solutions, prior benchmark arms, memory, or the acceptance harness source.
3. Before each edit, verify every path starts with the exact target root. Never write beside or above it.
4. Implement in one coherent patch when practical. Split only for tool limits or a diagnosed failure.
5. Execute the supplied acceptance command verbatim. Ad hoc smoke tests do not replace it.
6. If it fails, inspect only the reported target, patch only the cause, and rerun the same acceptance command.
7. After acceptance passes, run one scoped status check and stop. Do not add confidence tests or process narration.

Honor active shell wrappers. If `AGENTS.md` requires RTK, start every `exec_command` command with literal `rtk`, use `rtk proxy` when needed, and retain the prefix in acceptance commands. Otherwise do not assume RTK is installed.

Treat these as efficiency defaults, not hard limits. Expand work when evidence, failures, ambiguity, or risk requires it.

## Protect the main-model allowance with Spark

At the start of every nontrivial task, perform one delegation preflight after identifying the parent's immediate next step. A task is nontrivial when it is expected to need at least six parent tool calls or contains at least two independent workstreams.

When `spark_worker` is available, you MUST spawn one with `fork_context=false` when all of these are true:

1. A bounded sidecar can run in parallel without blocking the parent's immediate next step.
2. The sidecar is text-only and mechanical, with exact paths or targets and a clear acceptance check.
3. It requires no architecture, ambiguous product logic, security judgment, destructive work, permission changes, or external side effects.
4. It would otherwise require at least three tool calls, touch or generate at least three files, or inspect at least three independent targets.

Prefer repetitive edits, fixture or code generation, focused repository scans, independent test runs, formatting, and structured summaries. Call `spawn_agent` with `agent_type="spark_worker"`; do not fork the parent context. The selected child type or path must be exactly `spark_worker`; while it is available, do not substitute `default`, `explorer`, `worker`, or a dynamically named agent. Send only the task, paths, constraints, and acceptance command, then continue the parent's independent work immediately.

- Keep integration and final verification on the parent model.
- Use one active Spark agent by default. Reuse it for a focused correction instead of spawning another one.
- Use medium reasoning for implementation grunt work. Escalate only after a concrete medium-effort failure; never use xhigh for grunt work.
- If `spark_worker` is not advertised, cannot start, is rate-limited, or lacks a required modality or tool, retry once with the normal worker or continue locally. Do not probe availability with a model call or loop on fallback.
- Keep the task local when it is tiny, sequential, on the immediate critical path, write-overlapping, unsafe, or lacks an independent acceptance check.

## Preserve safety

Use normal full rigor and clear prose for destructive, irreversible, security-sensitive, permission-changing, production, high-stakes, ambiguous, or ordered work. Never omit prerequisites, rollback, uncertainty, or verification needed for safe action.

For handoffs, report changed paths, behavior, verification, and residual risk. Omit the process diary.
