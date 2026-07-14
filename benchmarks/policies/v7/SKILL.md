---
name: smart-compact-v7
description: Minimize parent-model token use with concise execution and adaptive parallel Spark delegation while preserving correctness and safety.
---

# Smart Compact v7 candidate

Minimize parent-model tokens without weakening correctness, safety, or scope.

- Do not create a plan for a bounded task. Inspect only inputs needed, batch independent reads, implement in one coherent patch, execute the supplied acceptance command verbatim, then stop after one scoped status check.
- Preserve exact requirements, code, commands, paths, identifiers, numbers, values, negation, and order. Honor active shell wrappers on every command and retry.
- Before broad inspection, split substantial independent mechanical work into named, nonoverlapping partitions. If the exact `spark_worker` role is available and its result can replace parent work, use the smallest concurrent worker set expected to remove the most parent work. There is no fixed count and maximum fan-out is not the goal: one worker may own several partitions, and another is justified only by material extra parent work avoided or critical-path parallelism.
- Give every worker exclusive inputs or write paths, wrapper constraints, and a deterministic result or acceptance contract. For path-disjoint work, let the worker inspect shared read-only contracts; the parent should not inspect worker implementation inputs unless integration requires it. Continue disjoint integration while workers run and do not repeat accepted work unless it fails or conflicts.
- Keep shared decisions, integration, and final deterministic acceptance on the parent. For aggregation, partition sources and validate the assembled artifact once.
- Stay local for tiny, sequential, overlapping, ambiguous, security-sensitive, destructive, externally stateful, or unverifiable work. If Spark is unavailable, continue locally without substituting another role.

Report only outcome, changed paths, decisive verification, blockers, and material residual risk.
