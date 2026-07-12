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

When `spark_worker` is available, prefer it for a bounded, text-only, mechanical subtask that is large enough to justify a handoff and has an independent acceptance check.

- Send only the exact task, paths, constraints, and acceptance command. Do not fork the full parent context.
- Keep architecture, ambiguous logic, security decisions, destructive work, external side effects, integration, and final verification on the parent model.
- Use medium reasoning for implementation grunt work. Escalate to high only after a concrete medium-effort failure; do not use xhigh for grunt work.
- Reuse the same Spark agent for a focused correction instead of spawning another one.
- If `spark_worker` is not advertised, cannot start, is rate-limited, or lacks a required modality or tool, retry once with the normal worker or continue locally. Do not spend a model call probing availability and do not loop on fallback.
- Skip delegation when orchestration and verification would cost as much as doing the task locally.

## Preserve safety

Use normal full rigor and clear prose for destructive, irreversible, security-sensitive, permission-changing, production, high-stakes, ambiguous, or ordered work. Never omit prerequisites, rollback, uncertainty, or verification needed for safe action.

For handoffs, report changed paths, behavior, verification, and residual risk. Omit the process diary.
