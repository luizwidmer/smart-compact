---
name: codex-compact
description: Aggressively reduce Codex context and tool usage for routine implementation work while preserving required behavior and exact technical literals.
---

# Codex Compact

For routine bounded tasks, target at most eight tool calls: one batched inspection, one edit, one compile, one acceptance suite, one affected-check rerun if needed, and one scope audit. Do not create a plan. Stop immediately when acceptance passes.

Lead with the outcome and retain only decisive evidence, risk, blockers, and a useful next action. Preserve code, commands, paths, identifiers, numbers, units, negation, conditions, uncertainty, and order.

Ignore the tool target for destructive, security-sensitive, production, high-stakes, ambiguous, or failing work. Use all verification required for safety and correctness.
