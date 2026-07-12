---
name: codex-compact
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

For bounded routine tasks:

- Skip a formal plan unless coordination or sequencing requires one.
- Batch independent reads and tool calls when safe.
- Inspect only inputs needed for the next decision.
- Prefer one implementation pass and one targeted verification command covering the acceptance criteria.
- Rerun only failed or affected checks. Reuse successful results after unrelated changes.
- Perform one final scope check, then stop when acceptance is proven.

Treat these as efficiency defaults, not hard limits. Expand work when evidence, failures, ambiguity, or risk requires it.

## Preserve safety

Use normal full rigor and clear prose for destructive, irreversible, security-sensitive, permission-changing, production, high-stakes, ambiguous, or ordered work. Never omit prerequisites, rollback, uncertainty, or verification needed for safe action.

For handoffs, report changed paths, behavior, verification, and residual risk. Omit the process diary.
