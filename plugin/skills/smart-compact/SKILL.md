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

Honor active shell wrappers. If `AGENTS.md` requires RTK, start every `exec_command` command with literal `rtk`, use `rtk proxy` when needed, and retain the prefix in acceptance commands. If the shell cannot resolve or launch a required wrapper, report that exact wrapper failure. If a wrapped command fails, diagnose or retry only through commands that retain the wrapper; never fall back to a raw command or absolute binary path. Otherwise do not assume RTK is installed.

Treat these as efficiency defaults, not hard limits. Expand work when evidence, failures, ambiguity, or risk requires it.

## Protect the main-model allowance with Spark

At the start of every nontrivial task, perform one delegation preflight after identifying the parent's immediate next step and before the second parent tool call. A task is nontrivial when it is expected to need at least six parent tool calls or contains at least two independent workstreams.

When `spark_worker` is surfaced by the spawn tool, you MUST select exactly that agent when all of these are true:

1. A bounded sidecar can run in parallel without blocking the parent's immediate next step.
2. The sidecar is text-only and mechanical, with exact paths or targets and a clear acceptance check.
3. It requires no architecture, ambiguous product logic, security judgment, destructive work, permission changes, or external side effects.
4. After batching related operations, it contains material homogeneous work across at least six exclusive files or independent targets. Tool-call count or the task's total size alone does not qualify the sidecar.
5. Either the user explicitly prioritizes preserving the parent-model allowance despite possible combined-token or latency overhead, or repeated paired measurements on a substantially similar workload demonstrate parent-token savings. Spark availability and a six-target count alone are not evidence of benefit.

Prefer repetitive edits, fixture or code generation, focused repository scans, independent test runs, formatting, and structured summaries. Keep work local when the task asks generally for speed or token efficiency but supplies neither an explicit parent-allowance objective nor workload-specific evidence; do not infer that objective from Spark availability. Use the surfaced spawn schema to select the exact `spark_worker` type or path. Disable context forking when the schema supports it; otherwise send only a self-contained task, paths, constraints, and acceptance command. The delegation brief MUST repeat every active shell-wrapper constraint, including the literal RTK prefix when required; do not assume the child inherits the parent's `AGENTS.md`. When RTK is active, also state that the inherited working directory is already the target root, shell `cd`/`chdir` is forbidden, and every command string's first word must be literal `rtk`. Give the sidecar exclusive paths or targets. Continue the parent's disjoint work immediately, then consume the handoff without repeating the child's inspection or edits unless it failed.

When correctness depends on counting, reconciliation, ordering, or deduplication across sources, delegate per-source evidence extraction with provenance unless the child has a deterministic acceptance check that covers the aggregate. The parent MUST own the final derived artifact and, before acceptance, run a deterministic source-to-artifact assertion that independently recomputes and compares every aggregate field. Visual counting, trusting the child total, or a public check that does not cover those fields is insufficient.

- Keep integration and final verification on the parent model.
- Use one active Spark agent by default. Reuse it for a focused correction instead of spawning another one.
- Use medium reasoning for implementation grunt work. Escalate only after a concrete medium-effort failure; never use xhigh for grunt work.
- If exact `spark_worker` selection is unsupported, unavailable, rate-limited, or lacks a required modality or tool, continue locally. Do not substitute another agent or repeatedly probe availability.
- Keep the task local when it is tiny, sequential, on the immediate critical path, write-overlapping, unsafe, or lacks an independent acceptance check.

## Preserve safety

Use normal full rigor and clear prose for destructive, irreversible, security-sensitive, permission-changing, production, high-stakes, ambiguous, or ordered work. Never omit prerequisites, rollback, uncertainty, or verification needed for safe action.

For handoffs, report changed paths, behavior, verification, and residual risk. Omit the process diary.
