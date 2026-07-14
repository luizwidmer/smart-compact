# Real-World Agentic Benchmark Research

Research snapshot: 2026-07-14.

## Scope

The proposed Smart Compact suite is a small, local evaluation of policy behavior. It borrows task shapes and evaluation principles from established agent benchmarks; it does not reproduce their datasets, environments, difficulty, or headline metrics. Results must therefore be reported only as Smart Compact results, never as SWE-bench, Terminal-Bench, OSWorld, or other benchmark-equivalent scores.

Fixtures should be offline, hermetic, resettable, and automatically graded. This reduces network and service drift and permits an exact paired comparison between Spark-enabled and no-Spark runs.

## Primary and official sources

| Source | Pattern borrowed | Important boundary |
| --- | --- | --- |
| [SWE-bench](https://github.com/SWE-bench/SWE-bench) and [SWE-bench Verified](https://openai.com/index/introducing-swe-bench-verified/) | Repository plus issue, hidden regression tests, containerized evaluation, and human review for solvability. Verified contains 500 screened tasks. | Local synthetic repositories are not SWE-bench instances and cannot be compared with its leaderboard. |
| [SWE-Lancer](https://openai.com/index/swe-lancer/) | End-to-end tests for bug fixes and feature work, plus task-value and difficulty framing. Its July 2025 update removed Internet dependence to reduce run variability. | Do not copy Upwork tasks or claim economic-value equivalence. |
| [Terminal-Bench 2.0](https://www.tbench.ai/benchmarks/terminal-bench-2) and its [paper](https://arxiv.org/abs/2601.11868) | Unique terminal environments, realistic build, dependency, data, and system-administration work, human-written solutions, and comprehensive tests. | Pin the pattern to 2.0's 89 published tasks. The current [2.1 page](https://www.tbench.ai/benchmarks/terminal-bench-2-1) says its tasks have not been uploaded. |
| [WorkArena and WorkArena++](https://github.com/ServiceNow/WorkArena) | Compositional knowledge work built from retrieval, forms, lists, dashboards, planning, and memory subtasks. | The local suite does not reproduce ServiceNow or browser interaction. |
| [TheAgentCompany](https://github.com/TheAgentCompany/TheAgentCompany) | A per-task initialized workplace containing instructions, workspace state, a result evaluator, and partial subcheckpoints across browsing, coding, program execution, and communication. | The local suite is not a simulated company and omits its services and multi-user environment. |
| [tau-bench paper](https://arxiv.org/abs/2406.12045), [tau3-bench v1.0.0](https://github.com/sierra-research/tau2-bench/releases/tag/v1.0.0), and [current evaluation specification](https://github.com/sierra-research/tau2-bench/blob/main/docs/evaluation.md) | Policy-bound retrieval and stateful tool use, multi-trial reliability, and final-state evaluation. | A reference action list is one valid path, not necessarily the only correct path. Score outcomes; use traces only for diagnosis. |
| [OSWorld 2.0](https://arxiv.org/abs/2606.29537) v1, 2026-06-28 | Long workflows with cross-source reasoning, implicit state, authentic artifacts, binary completion, partial credit, and a separate safety audit. | This is a recent preprint and a full computer-use benchmark. Use its design ideas, not its reported scores. |
| [ClawArena-Team](https://arxiv.org/abs/2606.31174) v2, 2026-07-02 | Execution-based subagent-management evaluation: task correctness, routing, least privilege, integration, and cost are measured separately. | Its parent agent is deliberately constrained and delegation is mandatory. Smart Compact's no-Spark arm must remain independently solvable. |
| [METR Time Horizon 1.1](https://metr.org/time-horizons/) | Human-duration estimates and success by difficulty/time band. | Do not publish a METR-style time horizon from a small suite intentionally containing parallelizable tasks. METR's long tasks are coherent units that cannot be trivially split. |

## Hermetic task design

The suite should combine delegation-positive work with negative controls:

1. multi-package issue-to-patch work with hidden regression tests;
2. broken dependency or build environments requiring terminal diagnosis;
3. incident triage across independent evidence shards followed by integrated repair;
4. release readiness spanning code, tests, configuration, changelog, and documentation;
5. policy retrieval followed by a stateful local update;
6. cross-source data workflows producing validated human- and machine-readable artifacts;
7. small sequential bugs where delegation is unnecessary; and
8. overlapping, risky, or architecture-heavy work where delegation is unsafe.

Every fixture must remain solvable by the parent without Spark and contain a clean initial snapshot, deterministic reset, user-facing specification, hidden outcome checks, oracle overlay used only for fixture validation, declared timeout and allowed filesystem scope, human solve-time estimate, and no required external network or mutable third-party service.

## Frozen v6 provenance

The v7 control is the exact v6 harness profile preserved by commit `14508ec3f0d4cfee86acbc2a639502bee33af037`, not the later expanded Smart Compact policy on `main`.

| Frozen artifact | Git object | Current benchmark copy |
| --- | --- | --- |
| `experiments/versions/v6-harness-profile/SKILL.md` | blob `47f91b8340685e87825aca2552d4ada2b61890e2` | [`benchmarks/policies/v6/SKILL.md`](benchmarks/policies/v6/SKILL.md) |
| `experiments/versions/v6-harness-profile/profile.config.toml` | blob `4d3e8166f6ea746ad191543ebeb9e9b66142c7ba` | [`benchmarks/profiles/v6.config.toml`](benchmarks/profiles/v6.config.toml) |
| `profiles/smart-compact.config.toml` at the same commit | blob `4d3e8166f6ea746ad191543ebeb9e9b66142c7ba` | Byte-identical to the frozen profile above. |

Historical v6 measurements remain background evidence only. The primary v7 comparison must run a fresh frozen `v6-spark` control under the same current parent model, reasoning setting, Codex runtime, tool surface, Spark role definition and availability, multi-agent capability, RTK version, fixture revision, timeout, and hardware class. Reusing the July 2026 token totals would confound policy effects with runtime and model drift.

## Historical four-case suite

The existing [`benchmarks/agentic-cases.json`](benchmarks/agentic-cases.json) contains an exploratory four-case suite. Its forced exactly-one-worker treatment and original split labels are historical and are not the v7 confirmatory design.

| Case | Historical role | Historical treatment |
| --- | --- | --- |
| `release-readiness` | Development negative control | Stay local. |
| `incident-triage` | Development offload case | Force one worker over six log shards. |
| `order-reconciliation` | Originally labeled held-out, but used during tuning | Force one worker over six CSV exports. |
| `ttl-boundary-regression` | Originally labeled held-out negative control | Stay local. |

The historical runner's hidden checks, allowed-path checks, role attribution, child completion, delegation-brief validation, acceptance-command observation, RTK audit, and per-thread token accounting fail closed. Those properties should be retained while replacing its fixed `expected_children` assumption with partition-aware adaptive fan-out.

## V7 ten-case suite

The executed suite contains six development cases and four held-out cases. Worker ranges are design envelopes, not targets: the policy should group named nonoverlapping partitions into the smallest useful concurrent worker set, and one worker may own multiple partitions.

| Case | Split | Planned task shape and partitions | Useful worker envelope |
| --- | --- | --- | ---: |
| `release-readiness` | Development | Existing five-target release reconciliation; negative control. | 0 |
| `incident-triage` | Development | Existing incident workflow partitioned as `logs-ab`, `logs-cd`, and `logs-ef`; read-only evidence. | 2–3 |
| `order-reconciliation` | Development | Relabeled existing data workflow partitioned as `central-coastal`, `east-north`, and `south-west`; read-only evidence. | 2–3 |
| `ttl-boundary-regression` | Development | Existing sequential boundary bug; negative control. | 0 |
| `monorepo-sdk-migration` | Development | New multi-package migration partitioned as `packages-ab`, `packages-cd`, `packages-ef`, and `packages-gh`; path-disjoint writes. One worker may own multiple partitions. | 1–4 |
| `offline-advisory-triage` | Development | New offline service advisory workflow partitioned as `services-ab`, `services-cd`, `services-ef`, and `services-gh`; read-only evidence. | 2–4 |
| `ci-matrix-root-cause` | Held-out | Multi-platform CI diagnosis with named platform partitions. | 2–4 |
| `tenant-config-drift` | Held-out | Configuration reconciliation across four tenant groups. | 2–4 |
| `support-credit-adjudication` | Held-out | Evidence-based adjudication across five ticket-pair partitions. | 3–5 |
| `permission-scope-regression` | Held-out | Sequential permission-boundary regression; negative control. | 0 |

The four held-out fixtures were created only after the candidate profile and policy were frozen. Before any matrix run, fixture audits strengthened the held-out and development oracles and the scorer's observable-evidence checks; the candidate profile, policy, and Spark worker bytes did not change. The final combined manifest and revised scorer hashes were frozen before execution.

## V7 adaptive fan-out protocol

The staged primary comparison is **`v6-spark` versus `v7-spark`** from the same clean fixture. Both arms expose the identical `spark_worker` definition and multi-agent capability so the frozen policy/profile is the changing factor. Neither prompt forces a worker count: the historical v6 policy may choose zero or more workers, while v7 applies its adaptive partition policy. A missing or unequal Spark capability makes the primary pair protocol-invalid rather than silently converting it to a no-Spark comparison.

Full confirmation adds explicit fallback arms:

| Arm | Policy | Spark and multi-agent availability | Purpose |
| --- | --- | --- | --- |
| `v6-spark` | Frozen v6 | Enabled with the frozen shared worker definition | Primary same-capability control. |
| `v7-spark` | Frozen v7 candidate | Identical to `v6-spark` | Primary policy treatment. |
| `standard-no-spark` | Standard control | Disabled and isolated from custom agents | No-Spark baseline. |
| `v7-no-spark` | Frozen v7 candidate | Disabled and isolated from custom agents | V7 local-fallback behavior. |

The no-Spark arms use an isolated Codex home with no custom-agent definition and multi-agent disabled. They are a separate fallback contrast, not substitutes for a failed `v6-spark` or `v7-spark` run.

Adaptive fan-out follows these rules:

1. Define named partitions, weights, allowed replication, input ownership, and write ownership before execution.
2. Spawn the smallest useful set of concurrent workers whose results can replace parent inspection or editing. A worker may own multiple partitions.
3. Add another worker only when the extra partitioning is expected to remove material parent work; maximum fan-out is not a success criterion.
4. Keep worker inputs read-only or writes path-disjoint. The parent owns shared decisions, integration, and one deterministic final acceptance check.
5. Continue disjoint parent integration while workers run, then consume correct worker results without repeating their work unless results fail, conflict, or leave coverage gaps.
6. Keep negative controls local. Any worker on a zero-worker control is over-delegation.

For every arm and trial:

1. Freeze model and inference settings, tool schema, dependency lock, hardware class, timeout, retry policy, and RTK treatment.
2. Materialize only seed files in a fresh Git repository; never expose gold overlays or hidden checks to the agent.
3. Randomize arm order within each paired block. Run independent case/trial blocks in parallel for throughput, while preserving the pair relationship.
4. A confirmatory publication normally requires at least three trials per case. Preserve every attempt, including failures, timeouts, unavailable workers, missed partitions, and over-delegation. A one-trial matrix must be labeled exploratory.
5. Grade final state and allowed paths rather than requiring one exact tool trajectory.
6. Keep profile-only measurement isolated from separately installed Smart Compact instructions so the policy is not duplicated.

Parallel blocks intentionally trade clean latency measurement for throughput. When `jobs > 1`, wall time is contention-affected and diagnostic only; token, quality, safety, partition, and routing metrics remain the release evidence.

## Objective and metric contract

V7 uses a lexicographic objective. Parent tokens saved per spawned Spark worker is the primary adaptive-fan-out optimization metric; absolute parent-token reduction remains the headline release outcome:

1. **Correctness, safety, and protocol validity are mandatory.** A failed task, scope escape, invalid worker role, incomplete required partition, or missing acceptance evidence cannot be traded for token savings.
2. **Among valid runs, maximize `parent_tokens_saved_per_spawned_worker` against the paired fresh `v6-spark` control while requiring material absolute parent-token savings.** Every spawn counts in the denominator, including workers that fail or contribute no unique correct partition.
3. **Among configurations with comparable savings efficiency and task coverage, choose the smallest spawned worker set and minimize coordination overhead.** More workers are not better by themselves.

Spark-worker tokens, combined parent-plus-worker tokens, and latency are required secondary disclosures. Parent-token savings must not be described as total-cost savings unless combined tokens also decline.

Keep these outcomes separate:

- `task_success`: hidden functional and artifact checks pass;
- `policy_success`: routing, partitioning, integration, and restraint satisfy the frozen policy;
- `protocol_valid`: environment, role, trace, usage, acceptance, scope, and RTK audits are complete and valid.

### Parent and system tokens

- parent input, cached-input, output, reasoning-output, and total tokens;
- child tokens by worker and in aggregate;
- combined parent-plus-child tokens;
- non-useful-child tokens from workers that contribute no unique correct partition;
- `parent_tokens_saved = parent_tokens_v6_spark - parent_tokens_v7_spark`;
- `parent_token_reduction = 1 - parent_tokens_v7_spark / parent_tokens_v6_spark`;
- `parent_tokens_saved_per_spawned_worker = parent_tokens_saved / spawned_workers`;
- `parent_tokens_saved_per_useful_worker = parent_tokens_saved / useful_workers` as a diagnostic only;
- `total_token_ratio = combined_tokens_v7_spark / combined_tokens_v6_spark`.

Per-worker savings metrics are `N/A` when their denominator is zero. Negative values must remain negative rather than being clipped.

### Adaptive fan-out and partition quality

- spawned, completed, and useful worker counts;
- useful-worker rate: `useful_workers / spawned_workers`, reported as a diagnostic rather than an optimization target;
- peak worker concurrency from child start-to-terminal intervals;
- weighted partition coverage: unique correctly completed partition weight divided by total required weight;
- per-child result correctness against its declared partition contract;
- useful-result score: the best correct result per partition, without duplicate credit;
- useful workers: workers contributing at least one unique correct partition;
- useful partitions per parent token, reported at a fixed scale such as per 1,000 parent tokens;
- duplicate work units: `sum(partition_weight * max(0, workers_touching_partition - allowed_replication))`;
- duplicate-work ratio: duplicate units divided by attempted partition weight;
- conflicting edits, scope escapes, integration repairs, parent corrections, time to first delegation, and idle wait.

For comparable fan-out configurations on the same case and runtime, report `marginal_parent_savings_per_extra_worker = change_in_parent_tokens_saved / change_in_spawned_workers`. Publish the Pareto frontier of valid configurations led by parent tokens saved per spawned worker, then absolute parent-token savings and correct partition coverage, while minimizing spawned workers, duplicate work, non-useful-child tokens, and combined tokens. Useful-worker count and rate diagnose routing quality but do not remove failed or redundant spawns from the primary denominator. A maximum-concurrency configuration is dominated when a smaller spawned worker set achieves comparable savings and quality.

### Quality, safety, and reliability

- binary task success and partial hidden subchecks;
- repeated-trial success and paired quality delta;
- timeout and unrecoverable-error rates;
- forbidden or out-of-scope mutations;
- destructive action without authorization;
- excessive worker permissions or overlapping writes;
- task and policy-constraint violations.

Publish every assigned run and paired effect. Three trials per case are a minimum reliability check, not a basis for strong confidence-interval or significance claims.

## Staged v7 tuning and confirmation

1. **Single-case tuning, complete:** tune only `monorepo-sdk-migration`, comparing `v7-spark` with a newly executed frozen `v6-spark` control under identical Spark role availability and multi-agent capability. Use its four path-disjoint package partitions to evaluate adaptive groups of one through four spawned workers, including one worker owning multiple partitions, and tune handoff size, join behavior, output limits, and compaction settings. Do not inspect the other nine fixtures for policy decisions during this stage.
2. **Candidate freeze, complete:** preserve immutable hashes for the selected v7 policy, profile, Spark worker configuration, development manifest, runner/scorer, runtime, and dependency lock in [`benchmarks/v7-freeze.json`](benchmarks/v7-freeze.json).
3. **Full matrix, complete:** run `v6-spark`, `v7-spark`, `standard-no-spark`, and `v7-no-spark` once across all six development and four held-out cases with randomized arm order. The user explicitly selected one pass rather than the proposed three repetitions, producing 40 total runs. Six runs executed concurrently for throughput.
4. **Exploratory publication, complete:** report all 40 attempts, task/policy/protocol outcomes, primary parent-token effects, secondary child and combined tokens, fan-out efficiency, partition coverage, and contention-labeled latency. Because every cell has one observation, these are exploratory measurements rather than repeated-trial estimates.

### Development-attempt ledger excluded from confirmation

| Attempt | Disposition | Reason or observed result |
| --- | --- | --- |
| `r1` | Invalid and excluded | The fixture contained a contradictory requirement, so neither policy comparison nor token effect was interpretable. |
| `r2` | Invalid and excluded | A scorer false negative invalidated the grade; it is harness-diagnostic evidence only. |
| `r3` | V7 arm valid; paired attempt excluded from confirmation | V7 passed routing. Frozen v6 had a genuine policy failure because parent and worker work overlapped; this was not a fixture or scorer defect. The single tuning attempt is not publishable confirmation. |

Preserve all three attempts and their diagnostics. Do not pool `r1` or `r2` into policy metrics, and do not present `r3` as confirmation because it preceded the candidate freeze and ran on the sole tuning case.

## V7 freeze and candidate-selection evidence

The final matrix freeze was recorded at `2026-07-14T19:54:43Z`. Fixture oracles and observable delegation evidence were hardened after candidate selection but before the full matrix; the selected profile, policy, and Spark agent bytes did not change. [`benchmarks/v7-freeze.json`](benchmarks/v7-freeze.json) records:

| Artifact | SHA-256 | Git blob |
| --- | --- | --- |
| `profiles/smart-compact-v7.config.toml` | `c264da8147f9f8a1de50b48b6eedab8dc1ada7f30fdf01400b60021639be58ce` | `3c1f2e7e6a24b4e90b4491c7dc4e6e48d8acdfb0` |
| `benchmarks/policies/v7/SKILL.md` | `d2aa1d3698fae44f17c15fdfcd460930103aa90da77af0353509dc8d1eda9b06` | `f2bb3ecd29eaba2c4e5d6c9b13dc66a503e7419b` |
| `.codex/agents/spark-worker.toml` | `aa82cdaea747994b8d356e3cf34301767508e47b483a9066d782c4e305bf39dd` | `759b109410074a8bba3c92bc02d44706cd2f940b` |
| `benchmarks/agentic-v7-development.json` | `643dcd0d7484128cc22745d0a1d3365ba89b07de1676bf091ddbbf5132d79b0f` | `50eddd83175c7a276a35135d13c3a463603b6660` |
| `benchmarks/agentic-v7-heldout.json` | `5e0f3593ba45d5d44ce448f06df2be14ac10957a85cef444f98e264d5e49eeb9` | `05425daaaf0ed840c2d3c5406dc848d0b1a17627` |
| `benchmarks/agentic-v7-confirmation.json` | `4c06aee473e7ddd4bbb6b492571874e9d5482514cf52af217d99e7b336466d84` | `3d2ec8eec8edb70cc4a14ee662028edf82195c73` |
| `scripts/benchmark_v7.py` | `d84723bc805822f9cdda60b39cd1f7407d0916ff253fa6f68e6d16e50280d432` | `5b3929dbee44e1356a5f64af4b62062af496680e` |
| `requirements-benchmark.txt` | `bb4e9a84677512c9085bf632fb963f8cd2cd6cdd42b45f4ddf29463cf38f04b0` | `77778b95ac65bf4c7fdd65c86b85fb921fde7ce6` |
| `benchmarks/results/v7-40-summary.json` | `2c0c0322628ef5e53a07b6d6e09ba88765fe0a849eadd9399c2a8ccfcedf5cff` | `39f71b5ccfbf09fff25c9abe6d42d2a9abdf412c` |

The frozen runtime is Codex `0.144.1`, RTK `0.43.0`, parent `gpt-5.6-luna` at high effort, and worker `gpt-5.3-codex-spark`.

The pre-hardening candidate-selection run covered only `monorepo-sdk-migration`: three trials per Spark arm, seed `20260717`, and `jobs=6`. V7 achieved 3/3 task and routing passes versus v6's 3/3 task and 2/3 routing passes. Paired medians were `80,619` parent tokens saved, `28.47%` parent-token reduction, and `80,619` parent tokens saved per spawned worker. One trial regressed by `17,212` parent tokens, so improvement was not uniform. This selected the candidate but is not pooled into the full-matrix metrics because the scorer was subsequently hardened.

## V7 single-pass 40-run matrix

The full matrix executed all ten cases and all four arms once, for exactly 40 assigned runs. Arm order was randomized with seed `20260718`; `jobs=6` made latency contention-affected. The compact per-run evidence and aggregates are in [`benchmarks/results/v7-40-summary.json`](benchmarks/results/v7-40-summary.json); its source raw artifact has SHA-256 `6e4c482a9b4cb6d82a03360f6fa0359783d6552dd5f6e835ce888f1e914d204a`.

| Arm | Task quality | Routing | Full policy success | Median parent tokens | Median child tokens | Median combined tokens | Median spawned/useful workers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `standard-no-spark` | 9/10 | 10/10 | 9/10 | 205,225 | 0 | 205,225 | 0 / 0 |
| `v6-spark` | 9/10 | 4/10 | 3/10 | 229,234 | 118,298 | 373,556.5 | 2 / 0 |
| `v7-no-spark` | 9/10 | 10/10 | 9/10 | 136,101.5 | 0 | 136,101.5 | 0 / 0 |
| `v7-spark` | 9/10 | 4/10 | 4/10 | 162,251.5 | 154,170.5 | 313,743.5 | 2 / 0 |

All arms failed the same `ci-matrix-root-cause` task, producing an equal mean quality score of `94.0`; the primary quality delta was therefore zero. Full policy success is stricter than task quality: it also requires correct worker roles, literal partition assignment, observable source evidence, nonoverlapping ownership, scope, acceptance, RTK compliance, and complete usage telemetry.

| Paired contrast | Parent-token wins | Median parent tokens saved | Median parent reduction | Median saved per spawned worker | Median combined reduction |
| --- | ---: | ---: | ---: | ---: | ---: |
| `v6-spark` → `v7-spark` | 8/10 | 41,894.5 | 30.153% | 34,765.667 | 17.693% |
| `standard-no-spark` → `v7-no-spark` | 8/10 | 59,516.5 | 31.593% | N/A | 31.593% |
| `v7-no-spark` → `v7-spark` | 1/10 | -15,380.5 | -10.4755% | -11,236.5 | -141.691% |

The primary same-capability result is favorable to v7: it used fewer parent tokens than frozen v6 in eight cases, with a paired median `30.153%` parent reduction and `17.693%` combined reduction at equal task quality. The strongest overall parent-token result, however, was v7 with Spark disabled. Enabling Spark on the same v7 profile increased paired median parent use by `10.4755%` and combined use by `141.691%`, winning parent tokens in only one case. This means the profile improvements are supported, while Spark offload remains a selectively gated capability rather than a default token-saving mechanism.

The median useful-worker count was zero under the hardened evidence definition because many completed workers did not evidence every assigned source marker or literal partition contract. Spawned workers still count fully in the primary efficiency denominator. This exposes the current routing weakness instead of treating completed but unauditable workers as free savings.

These are complete single-pass observations, not repeated-trial estimates. The runner therefore marks confirmatory quality and token publication false under its three-trial rule, and latency is non-publishable under parallel contention. The matrix is suitable for an exploratory v7 release note, not statistical confidence or production-generalization claims.

## Historical exactly-one matrix: 2026-07-14

This section is retained only as exploratory evidence that motivated adaptive fan-out. It is not a v7 result, does not use the planned ten-case suite, and must not be used as the frozen-v6 control.

The historical four-case matrix completed 24/24 runs and 12/12 valid pairs with full hidden-check quality. Its treatment forced exactly one worker on six eligible Spark runs; all six completed, while six Spark-available negative controls and all 12 no-Spark runs created no child. Scope, acceptance-command, usage-accounting, and RTK audits passed 24/24.

| Arm | Runs | Success | Median parent tokens | Median combined tokens | Median duration* |
| --- | ---: | ---: | ---: | ---: | ---: |
| No-Spark | 12 | 12/12 | 123,686 | 123,686 | 61.113s |
| Spark-available | 12 | 12/12 | 168,805 | 182,899 | 74.805s |

Across all 12 historical pairs, the Spark-available arm's median within-pair change was +28.15% parent tokens and +37.3% combined tokens. Positive values mean more consumption. Wall time was contention-affected because three case/trial blocks ran concurrently. The result supports neither a general token-saving claim nor a fixed-one-worker policy; it motivates measuring whether adaptive partitioning can remove enough parent work to justify each worker.

## Limitations

- Synthetic local tasks omit organizational context, evolving requirements, live users, browser drift, and many GUI failures.
- Ten task templates and three minimum trials per case remain too small for broad significance or time-horizon claims.
- Model and tool behavior is stochastic even under matched settings; fresh paired controls are required.
- Provider accounting, caching, and hidden system overhead may differ from recorded token telemetry.
- Parallel-block latency is contention-affected and cannot establish clean speedup.
- Shared-workspace workers can introduce races absent from read-only delegation; path ownership must be audited.
- Partition definitions and weights can bias coverage and usefulness metrics, so they must be frozen before confirmation.
- Public benchmark patterns may appear in training data; locally authored held-out fixtures reduce but do not eliminate overfitting.
- Recent sources such as OSWorld 2.0 and ClawArena-Team are preprints and may change.
- The suite evaluates policy, profile, worker scaffold, and model together; it does not isolate raw model capability.
