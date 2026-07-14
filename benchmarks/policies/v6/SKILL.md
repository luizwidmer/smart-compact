---
name: codex-compact
description: Reduce Codex context replay and visible output with an exact acceptance contract, scoped edits, concise handoffs, and normal safety rigor.
---

# Smart Compact

Optimize total task context without compressing requirements, code, commands, or hidden reasoning.

For a bounded local task with a complete specification, one owner, an exact target root, and a supplied acceptance command:

1. Do not create a plan or reread instructions already in context.
2. Read only the specification and target state needed to implement. Do not inspect sibling solutions, prior benchmark arms, memory, or the acceptance harness source.
3. Before each edit, verify every path starts with the exact target root. Never write beside or above it.
4. Implement in one coherent patch when practical. Split only for tool limits or a diagnosed failure.
5. Execute the supplied acceptance command verbatim. Ad hoc smoke tests do not replace it.
6. If it fails, inspect only the reported target, patch only the cause, and rerun the same acceptance command.
7. After acceptance passes, run one scoped status check and stop. Do not add confidence tests or process narration.

Honor active shell wrappers. If `AGENTS.md` requires RTK, start every `exec_command` command with literal `rtk`, use `rtk proxy` when needed, and retain the prefix in acceptance commands. Otherwise do not assume RTK is installed.

These are workflow defaults, not a hard call budget. Expand when failure, ambiguous requirements, destructive impact, security, permissions, production, or high-stakes risk requires it.

Communicate only the outcome, changed paths, decisive verification, blocker, and material residual risk. Preserve exact identifiers, numbers, values, negation, conditions, and order.
