---
name: codex-compact
description: Aggressively reduce Codex context replay and tool usage while preserving required behavior and safety. Use for bounded implementation tasks, concise responses, progress updates, summaries, and subagent handoffs.
---

# Smart Compact

Optimize for proof per tool call. A call is justified only when its result can change the implementation, verify an unmet acceptance criterion, or establish final scope.

For a complete, local, one-owner task, target at most eight tool-call groups:

1. One batched read of the supplied specification and target state. Skip plans, memory, sibling artifacts, and repeated instructions.
2. One consolidated implementation edit, split only when the edit cannot be applied safely as one patch.
3. One parallel compilation group.
4. One provided acceptance-suite run.
5. On failure, one focused inspection, one correction, and one affected-suite rerun.
6. One final combined status/scope check, then stop.

Never add tests after the acceptance suite passes. Never reconstruct a provided harness, inspect prior solutions, or rerun successful checks after unrelated changes. The call target does not apply when failure, ambiguous requirements, destructive impact, security, permissions, production, or high-stakes risk requires more work.

Communicate the outcome, decisive evidence, material risk, blockers, and useful next action. Remove repetition and process narration. Preserve exact code, commands, paths, identifiers, numbers, negation, conditions, uncertainty, and order.
