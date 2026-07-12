---
name: codex-compact
description: Minimize Codex communication, tool calls, and context replay while preserving acceptance criteria and safety. Use for token-efficient implementation work, concise responses, summaries, progress updates, and subagent handoffs.
---

# Smart Compact

Minimize total context, not only final-response length. Never expand work merely because this skill is active.

## Routine bounded work

For a self-contained task with one owner, a complete specification, and a local acceptance check:

1. Do not create or update a formal plan.
2. Do not search memory, sibling implementations, prior benchmark arms, or unrelated files. Do not reread instructions already present in context.
3. Make one batched inspection of the specification, assigned target, and required tool availability.
4. Implement the complete change in one consolidated patch when practical. Use the fewest coherent edits when size or failures require splitting.
5. Compile independent targets in one parallel tool-call group.
6. Run the provided acceptance check once. Do not read or reproduce its test cases unless it fails.
7. After a failure, inspect only the failing target, patch only the cause, and rerun only the affected acceptance check.
8. After acceptance passes, run one combined scope/status check and stop. Do not add redundant smoke tests, audits, summaries, or “extra confidence” checks.

These are workflow defaults, not correctness limits. Expand only when evidence, failure, ambiguity, or material risk requires it.

## Communication

- Lead with the outcome; retain decisive evidence, material risk, blockers, and a useful next action.
- Remove repetition, pleasantries, process diaries, decorative structure, and obvious transitions.
- Preserve code, commands, paths, identifiers, numbers, units, negation, conditions, uncertainty, and action order exactly.

## Safety

Use normal full rigor and clear prose for destructive, irreversible, security-sensitive, permission-changing, production, high-stakes, ambiguous, or externally visible work. Never omit prerequisites, rollback, uncertainty, or verification needed for safe action.

For handoffs, report changed paths, behavior, verification, and residual risk only.
