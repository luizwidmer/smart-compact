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

## Proposed hermetic task shapes

The suite should include delegation-positive work and negative controls:

1. A multi-package issue-to-patch task with hidden regression tests.
2. A broken dependency or build environment requiring terminal diagnosis and repair.
3. Incident triage across independent log shards, followed by one integrated fix and postmortem.
4. Release readiness spanning code, tests, configuration, changelog, and documentation.
5. Policy and knowledge retrieval over a local document corpus followed by a stateful JSON or SQLite update.
6. A cross-source data workflow producing a validated report and machine-readable artifact.
7. A small, sequential bug where delegation is unnecessary.
8. An architecture, security, or write-overlapping task where delegation is unsafe or counterproductive.

Cases 1-6 should be explicitly labeled `offload_expected: true` only when they satisfy the policy's stated Spark preconditions. Cases 7-8 should be labeled `offload_expected: false` and measure over-delegation. Every case must remain solvable without Spark.

Each fixture should contain:

- a clean initial snapshot and deterministic reset;
- a user-facing task specification;
- hidden outcome checks and optional partial subchecks;
- an oracle solution used only to prove fixture solvability;
- a declared runner timeout and allowed filesystem scope, plus any token budget when one is actually enforced;
- a human solve-time estimate or measured baseline;
- no required external network or mutable third-party service.

## Implemented local suite

[`benchmarks/agentic-cases.json`](benchmarks/agentic-cases.json) currently freezes four stdlib-only cases:

| Case | Split | Task shape | Experimental treatment |
| --- | --- | --- | --- |
| `release-readiness` | Development | Reconcile package metadata, plugin metadata, changelog, and installation documentation. | Stay local as a five-target break-even control. |
| `incident-triage` | Development | Reconcile six log shards, repair retry behavior, and produce a machine-readable incident report with precisely defined status semantics. | Force offload of the six-source evidence pass in the Spark arm; require a parent-side source-to-artifact assertion for the final aggregate. |
| `order-reconciliation` | Held-out | Reconcile six regional CSV exports into a reusable script, JSON summary, and report. | Force homogeneous source analysis into the Spark arm. |
| `ttl-boundary-regression` | Held-out | Diagnose and fix one exact cache-expiration boundary bug. | Stay local as a sequential negative control. |

The runner materializes only each case's seed files into a fresh Git repository. Gold overlays prove that every fixture is solvable but are never copied into the agent workspace. Hidden checks, allowed-path checks, exact Spark-role attribution, completed-child checks, semantic delegation-brief checks, acceptance-command observation, RTK command auditing, and internally consistent per-thread token accounting all fail closed. In this suite, `offload_expected: true` identifies a forced experimental treatment, not a recommendation that the current default policy should automatically offload that task.

## Paired Spark/no-Spark protocol

Run every case in both arms from the same clean fixture. Independent case/trial pairs may run concurrently, but the two arms inside each pair stay sequential in seeded randomized order:

- **Spark-enabled:** the Spark worker is available. Treatment-positive workloads use the same conditional prompt in both arms to assign exactly one six-source read-only sidecar when `spark_worker` exists; a missed spawn remains a routing failure. Local-control workloads exercise autonomous restraint and must not spawn.
- **No-Spark:** Spark is unavailable. The runner starts from an isolated ephemeral Codex home containing authentication but no custom-agent definition; `features.multi_agent=false` is also set at process and thread scope. Keep the parent model, policy text, task prompt, budgets, runtime, and fixture otherwise identical.

The conditional treatment sentence is identical in both arms: use exactly one `spark_worker` when that role is available, otherwise complete the same evidence pass locally without substituting another agent. This prevents stochastic treatment crossover in the offload A/B while the separate policy oracle continues to test autonomous threshold decisions.

For both arms:

1. Freeze the model and inference settings, policy commit, tool schema, dependency lock, hardware class, timeout, and retry policy.
2. Reset the fixture before every attempt and randomize arm order.
3. Run at least three trials per case; five is preferable when cost permits.
4. Preserve all attempts, including failures, timeouts, and missed delegations.
5. Grade final files, database state, commands, and tests. Do not require one exact tool-call trajectory unless the task genuinely has only one valid path.
6. Keep worker writes read-only or path-disjoint where possible. Treat write collisions and integration repairs as measured failures or overhead, not harness noise.

For profile-only measurement, the runner sets `project_doc_max_bytes=0` and disables the separately installed Smart Compact skill so machine-global instructions cannot duplicate the profile policy. It then adds only the same strict RTK command constraint to both arms. Raw workspaces and run JSON remain generated artifacts outside Git.

Headline comparisons should use all assigned runs. A spawned-only analysis may be published as a diagnostic, but it must not replace the Spark-available versus Spark-unavailable comparison.

## Metric contract

The following is the target metric set for continued suite development. The current runner aggregates the quality, routing, completion, scope, acceptance, RTK, usage, tool-call, and time fields represented in its result schema; it does not yet aggregate every coordination diagnostic below.

### Quality and reliability

- binary task success;
- partial subchecks passed, reported alongside full success;
- paired success delta between arms;
- success by task family and human-duration band;
- repeated-trial success and a clearly defined multi-trial reliability statistic;
- timeout and unrecoverable-error rates.

### Token and time efficiency

- parent input, cached-input, and output tokens;
- Spark worker tokens;
- total system tokens across parent and workers;
- parent and worker tool calls;
- end-to-end wall time and time to first delegation;
- `parent_token_reduction = 1 - parent_tokens_spark / parent_tokens_no_spark`;
- `total_token_ratio = total_tokens_spark / total_tokens_no_spark`;
- `wall_time_speedup = wall_time_no_spark / wall_time_spark`.

Parent-token savings must never be presented as total-cost savings unless total system tokens also decline.

### Delegation and coordination

- delegation recall: eligible cases with a Spark spawn divided by eligible cases;
- over-delegation rate: ineligible cases with a Spark spawn divided by ineligible cases;
- worker completion and useful-result rates;
- duplicated investigation or tool calls;
- conflicting edits, scope escapes, and merge/integration failures;
- parent corrections after worker return;
- idle wait and coordination overhead.

### Safety

- forbidden or out-of-scope mutations;
- destructive action without authorization;
- excessive permissions granted to a worker;
- policy or task-constraint violations;
- success conditional on zero safety violations.

Publish quality, parent-token use, total-token use, time, and orchestration as separate dimensions. With only three trials per case, report every paired effect without inferential or confidence-interval claims. A Pareto view is more informative than one composite score.

## Measured matrix: 2026-07-14

The post-RTK-fine-tune matrix completed 24/24 assigned runs and 12/12 valid pairs. Both arms achieved 100% hidden-check quality. Eligible Spark routing was 6/6 with the exact `spark_worker`, completed-child status was 6/6, and the six negative-control Spark-available runs created no child. No-Spark created no child in 12/12 runs. Scope, delegation-brief, acceptance-command, usage-accounting, and RTK audits passed 24/24.

| Arm | Runs | Success | Median parent tokens | Median combined tokens | Median duration* |
| --- | ---: | ---: | ---: | ---: | ---: |
| No-Spark | 12 | 12/12 | 123,686 | 123,686 | 61.113s |
| Spark-available | 12 | 12/12 | 168,805 | 182,899 | 74.805s |

| Scope | Pairs | Parent-token change | Combined-token change | Wall-time change* |
| --- | ---: | ---: | ---: | ---: |
| All assigned runs | 12 | +28.15% | +37.3% | +22.5% |
| Actually offloaded diagnostic | 6 | +31.35% | +50.2% | +26.65% |
| No-offload controls | 6 | +15.9% | +15.9% | +11.95% |

Positive changes mean the Spark-available arm used more tokens or time. These effects are medians of within-pair percentage changes, so they need not equal ratios of the pooled arm medians. `*` Wall time is contention-affected because three case/trial pairs ran concurrently; it is diagnostic, not a clean latency comparison.

Per-case marginal medians provide additional scale context:

| Case | Arm | Parent | Child | Combined | Duration* |
| --- | --- | ---: | ---: | ---: | ---: |
| `release-readiness` | No-Spark / Spark | 101,870 / 112,112 | 0 / 0 | 101,870 / 112,112 | 60.604s / 64.129s |
| `incident-triage` | No-Spark / Spark | 233,558 / 216,364 | 0 / 41,481 | 233,558 / 286,036 | 97.929s / 97.605s |
| `order-reconciliation` | No-Spark / Spark | 146,732 / 226,919 | 0 / 31,011 | 146,732 / 257,930 | 62.716s / 113.079s |
| `ttl-boundary-regression` | No-Spark / Spark | 64,675 / 64,715 | 0 / 0 | 64,675 / 64,715 | 25.626s / 27.164s |

Reproducibility metadata: parent `gpt-5.6-luna` at high effort; worker `gpt-5.3-codex-spark`; Codex `0.144.2`; RTK `0.43.0`; three trials per case and arm; `jobs=3`; seed `20260714`; cases SHA-256 `ac0d2d1a0907ec60bbe691aced8551ed2d21da31b14476453c4e9ab2c1e37d70`; treatment-profile SHA-256 `055919d98461aefe480ea06bb48a21cddc5faf08849d57ea12b8662aa7d8aa9b`; worker SHA-256 `aa82cdaea747994b8d356e3cf34301767508e47b483a9066d782c4e305bf39dd`.

The matrix validates quality-preserving treatment execution, exact routing, and local fallback. It does not reproduce the historical single-run parent-allowance saving and does not support Spark as a general token or latency optimization. After observing this result, the default automatic policy was tightened to require either an explicit user parent-allowance objective or repeated paired benefit on a substantially similar workload. `publishable=true` in the generated artifact means only that the runner's completeness and audit predicates passed; it is not a statistical or external-validation label.

## Tuning and evaluation splits

Split the suite before changing the policy:

- **Development split:** used to diagnose delegation thresholds, handoff wording, worker scope, and join behavior.
- **Held-out split:** unseen task templates or materially different fixtures, not merely renamed copies or new seeds from the same template.

For a future confirmatory release, tune only on development cases, freeze the selected policy, then run the complete baseline and tuned policy on an untouched evaluation split under both Spark arms. Publish the frozen versions, all run counts, exclusions, failures, and any deviations from the preregistered protocol. If an evaluation fixture is found broken, document the defect and rerun every compared policy on the corrected version.

The current `order-reconciliation` fixture participated in implementation tuning even though its manifest label is `held-out`; this matrix therefore makes no untouched-held-out generalization claim. The supported release claim is narrower: **quality and routing parity for the forced Spark/no-Spark treatment on this local suite, with a measured token regression and contention-affected time disclosed**.

## Limitations

- Synthetic local tasks approximate real work but omit organizational context, evolving requirements, live users, browser drift, and many GUI failures.
- A small suite has wide uncertainty and may not support strong significance or time-horizon claims.
- Model and tool runtimes remain stochastic even with matched settings; repeated paired trials are required.
- Token accounting can differ by provider, caching implementation, and hidden system overhead.
- Wall time depends on hardware load and concurrency; this matrix's `jobs=3` values are not a controlled latency comparison.
- Shared-workspace Spark runs can introduce write races that do not exist in read-only delegation.
- Public benchmark tasks may appear in training data; locally authored future evaluation fixtures can reduce but do not eliminate policy overfitting.
- Recent sources such as OSWorld 2.0 and ClawArena-Team are preprints and may change.
- The suite evaluates Smart Compact's policy and available agent scaffold together; it does not isolate raw model capability.
