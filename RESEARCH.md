# Real-World Agentic Benchmark Research

Research snapshot: 2026-07-14.

## Scope

The Smart Compact suite is a small local evaluation of agent policy behavior. It borrows task shapes and evaluation principles from established benchmarks; it does not reproduce their datasets, environments, difficulty, or headline metrics. Results are Smart Compact results, not SWE-bench, Terminal-Bench, OSWorld, or other benchmark-equivalent scores.

Fixtures are offline, hermetic, resettable, and automatically graded. Every case remains solvable by the parent without Spark.

## Primary and official sources

| Source | Pattern borrowed | Important boundary |
| --- | --- | --- |
| [SWE-bench](https://github.com/SWE-bench/SWE-bench) and [SWE-bench Verified](https://openai.com/index/introducing-swe-bench-verified/) | Repository plus issue, hidden regression tests, containerized evaluation, and human review for solvability. | Local synthetic repositories are not SWE-bench instances and cannot be compared with its leaderboard. |
| [SWE-Lancer](https://openai.com/index/swe-lancer/) | End-to-end tests for bug fixes and feature work, plus task-value and difficulty framing. | Do not copy Upwork tasks or claim economic-value equivalence. |
| [Terminal-Bench 2.0](https://www.tbench.ai/benchmarks/terminal-bench-2) and its [paper](https://arxiv.org/abs/2601.11868) | Unique terminal environments, realistic build, dependency, data, and system-administration work. | The local suite borrows task shapes, not Terminal-Bench tasks or scores. |
| [WorkArena and WorkArena++](https://github.com/ServiceNow/WorkArena) | Compositional knowledge work built from retrieval, forms, lists, dashboards, planning, and memory subtasks. | The local suite does not reproduce ServiceNow or browser interaction. |
| [TheAgentCompany](https://github.com/TheAgentCompany/TheAgentCompany) | Per-task initialized workplaces, workspace state, evaluators, and partial subchecks. | The local suite is not a simulated company and omits its services and multi-user environment. |
| [tau-bench](https://arxiv.org/abs/2406.12045) and its [evaluation specification](https://github.com/sierra-research/tau2-bench/blob/main/docs/evaluation.md) | Policy-bound retrieval, stateful tool use, multi-trial reliability, and final-state evaluation. | A reference action list is one valid path, not necessarily the only correct path. |
| [OSWorld 2.0](https://arxiv.org/abs/2606.29537) | Long workflows, authentic artifacts, binary completion, partial credit, and separate safety auditing. | Use its design ideas, not its scores. |
| [ClawArena-Team](https://arxiv.org/abs/2606.31174) | Execution-based subagent evaluation across correctness, routing, least privilege, integration, and cost. | Smart Compact keeps no-Spark cases independently solvable. |
| [METR Time Horizon 1.1](https://metr.org/time-horizons/) | Human-duration estimates and success by difficulty band. | This suite is too small and intentionally parallelizable, so it does not support a METR-style time-horizon claim. |

## Hermetic task design

The suite combines multi-package migration, terminal diagnosis, incident response, release readiness, policy-bound updates, cross-source reconciliation, sequential negative controls, and security-sensitive work. Each fixture contains a clean initial snapshot, deterministic reset, user-facing specification, hidden outcome checks, an oracle used only for fixture validation, allowed-path constraints, a human solve-time estimate, and no required external network or mutable third-party service.

## Frozen v6 and the v7 gap

V6 is the exact harness profile preserved by commit `14508ec3f0d4cfee86acbc2a639502bee33af037`, not a reconstruction from later `main` content.

| Frozen artifact | Git object | Benchmark copy |
| --- | --- | --- |
| `experiments/versions/v6-harness-profile/SKILL.md` | `47f91b8340685e87825aca2552d4ada2b61890e2` | [`benchmarks/policies/v6/SKILL.md`](benchmarks/policies/v6/SKILL.md) |
| `experiments/versions/v6-harness-profile/profile.config.toml` | `4d3e8166f6ea746ad191543ebeb9e9b66142c7ba` | [`benchmarks/profiles/v6.config.toml`](benchmarks/profiles/v6.config.toml) |

The v8 comparison executes fresh Standard, frozen-v6, and v8 no-Spark controls on the same current task and runtime. Historical v6 calculator totals remain background evidence only. V7 exposed useful gaps in routing and fan-out evaluation, but it was not rerun; v8 is compared directly with Standard and frozen v6.

## V8 suite

The confirmation manifest contains four development and six held-out fixtures. Worker counts are uncapped; the policy must choose the smallest useful set.

| Case | Split | Task shape | Auto-routing expectation |
| --- | --- | --- | --- |
| `release-readiness` | Development | Repository release reconciliation | Stay local |
| `incident-triage` | Development | Independent incident evidence shards | Delegate |
| `monorepo-sdk-migration` | Development | Path-disjoint multi-package migration | Forced-efficacy case |
| `offline-advisory-triage` | Development | Offline dependency-security workflow | Delegate |
| `ci-matrix-root-cause` | Held-out | Multi-platform CI diagnosis | Delegate |
| `tenant-config-drift` | Held-out | Configuration reconciliation | Delegate |
| `support-credit-adjudication` | Held-out | Evidence-based back-office workflow | Delegate |
| `permission-scope-regression` | Held-out | Sequential permission-boundary repair | Stay local |
| `multi-service-contract-rollout` | Held-out | Multi-service API migration | Delegate |
| `policy-bound-batch-update` | Held-out | Stateful policy workflow | Stay local |

## Objective and matrix

The v8 objective is lexicographic:

1. Task correctness, safety, and allowed scope are mandatory.
2. Minimize parent-model tokens.
3. When parent-token savings are small, prefer lower wall time.
4. Prefer the fewest spawned workers for the achieved parent-token or wall-time saving.

Child and combined tokens are required disclosures, not the optimization target. Every spawned worker stays in the efficiency denominator, including redundant or non-useful workers.

| Arm | Cells | Purpose |
| --- | ---: | --- |
| `standard-no-spark` | 4 | Current no-profile control on the migration case at four parent settings |
| `v6-no-spark` | 4 | Frozen-v6 control on the same four settings |
| `v8-no-spark` | 13 | Ten-case Luna/xhigh suite plus three additional migration settings |
| `v8-spark-forced` | 4 | One exact harness-started Spark worker on the migration case at each setting |
| `v8-spark-auto` | 9 | Native parent routing on the other nine Luna/xhigh cases |
| **Release matrix** | **34** | One observation per cell |

The four parent settings are `gpt-5.6-sol` medium/high and `gpt-5.6-luna` xhigh/max. Spark is `gpt-5.3-codex-spark` at medium effort. Forced-efficacy blocks used `jobs=1`; the nine-case auto-routing block used `jobs=4`. Seed `20260721` is fixed throughout.

Six development-selection runs tuned automatic compaction and tool-output history before release scoring. The selected profile uses the native automatic-compaction default and a 1,500-token tool-output limit. Those six tuning cells plus 34 release cells make 40 scored observations.

## Freeze and selection provenance

The profile was initially frozen at `2026-07-14T21:14:07Z` and refrozen at `2026-07-15T00:18:49Z` after the parent, worker, and compaction handoffs were rewritten as terse machine key-value contracts. Six failed Spark gates and five pre-rewrite release cells informed that rewrite; none is pooled into v8 metrics. Six cells from an interrupted first post-rewrite batch are also superseded. This is transparent engineering selection, not an untouched statistical holdout.

| Frozen artifact | SHA-256 |
| --- | --- |
| [`profiles/smart-compact-v8.config.toml`](profiles/smart-compact-v8.config.toml) | `b3e4658e957811c69640351cb2302b759ff0a1811bc83fab5b08dbbf63a4e48c` |
| [`benchmarks/policies/v8/SKILL.md`](benchmarks/policies/v8/SKILL.md) | `44fbe5838731fa6d25af293a780557bf1e32a93dd5eb5de0e45b6b1a1dcaf327` |
| [`.codex/agents/spark-worker.toml`](.codex/agents/spark-worker.toml) | `ac0aaa80e9a8a5ee4c7a7d83cc048af69d44ac6856103734b2c3ff3505af0c68` |
| [`benchmarks/agentic-v8-development.json`](benchmarks/agentic-v8-development.json) | `90770e2ae247acd4bfbaba9323e2197bc90b8e7c64b9d4037891c2fa3d5b12ac` |
| [`benchmarks/agentic-v8-heldout.json`](benchmarks/agentic-v8-heldout.json) | `669469a7b42acd01e023b851f0402f06c8e3436f93dd6d145fb98a2a1690dfb3` |
| [`benchmarks/agentic-v8-confirmation.json`](benchmarks/agentic-v8-confirmation.json) | `968c222cf82c41b77ce1bbc37b0cc426ae4cd5a4139c83690abc81d0b434d534` |
| [`scripts/benchmark_v8.py`](scripts/benchmark_v8.py) | `8f9b2e3a8d8c47a74f093ac56f0fc0a8903b4f4890cc2004be70a60cb0082f43` |
| [`scripts/verify_v8_release.py`](scripts/verify_v8_release.py) | `4e7de7b96b0f855a0a111918e9d88a3b0d84e695eaff2f350e045a979661f2c5` |
| [`requirements-benchmark.txt`](requirements-benchmark.txt) | `bb4e9a84677512c9085bf632fb963f8cd2cd6cdd42b45f4ddf29463cf38f04b0` |

### Timeout and retry selection

The original Luna/xhigh four-arm source, SHA-256 `11c04490eb8f9b92ce7155b89b1390b04c7d3650187ca906144b6aea6ed371dd`, completed Standard, v8 no-Spark, and forced Spark. Its v6 cell encountered upstream 503 and stream disconnects until the 900-second turn timeout. [`benchmarks/results/v8-release-luna-xhigh-selection.json`](benchmarks/results/v8-release-luna-xhigh-selection.json), SHA-256 `364a46057d499a5cedf1ef641ccec8f5bfa5ce6f084c92646779b46d26508d2f`, selects the three completed cells and records the exclusion. An isolated same-seed v6 retry, SHA-256 `b88778d53651494032afc37d3ad4019d83dc9939ce9eb63c4e0be4481542409b`, supplies the missing control. No failed attempt is averaged into the reported result.

| Selected release source | SHA-256 | Cells |
| --- | --- | ---: |
| `v8-release-sol-medium-terse-r2.json` | `79fe5cce23097a33b2c87a557433ddfb645ec005edb8d406ab0840e89cd614cb` | 4 |
| `v8-release-sol-high-terse-r2.json` | `df95bb72a95b5a5b15bb61677d9e2fa4a8daf777927f5c1ce2f10c2297c85b26` | 4 |
| `v8-release-luna-max-terse-r2.json` | `73eacdc6e16ba6f911525d4f7d6d30e14d8fbba15e30833b56544f851034b068` | 4 |
| `v8-release-primary-luna-xhigh-terse-r2.json` | `0743ba2cb113d5e7e5228f4b9cd16c4e3c4c942b1003b5ce6b76b3f3fc6ad895` | 18 |
| `v8-release-luna-xhigh-terse-r2.json` through the selector | `11c04490eb8f9b92ce7155b89b1390b04c7d3650187ca906144b6aea6ed371dd` | 3 |
| `v8-release-v6-luna-xhigh-retry-terse-r2.json` | `b88778d53651494032afc37d3ad4019d83dc9939ce9eb63c4e0be4481542409b` | 1 |

## V8 results

Task correctness is the release gate and passed 34/34. The secondary audit recorded 26/34 full protocol compliance and 33/34 RTK compliance; neither miss changed the graded final artifacts.

### Standard to v6 to v8, no Spark

All rows use `monorepo-sdk-migration`; all 12 arm/settings cells passed.

| Parent model / effort | Standard parent tokens | V6 parent tokens | V6 saved vs Standard | V8 no-Spark parent tokens | V8 saved vs Standard | V8 saved vs v6 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `gpt-5.6-sol` / medium | 125,857 | 193,980 | -68,123 (-54.127%) | 117,286 | 8,571 (6.810%) | 76,694 (39.537%) |
| `gpt-5.6-sol` / high | 131,074 | 206,214 | -75,140 (-57.326%) | 100,218 | 30,856 (23.541%) | 105,996 (51.401%) |
| `gpt-5.6-luna` / xhigh | 220,872 | 348,084 | -127,212 (-57.595%) | 251,845 | -30,973 (-14.023%) | 96,239 (27.648%) |
| `gpt-5.6-luna` / max | 315,109 | 714,788 | -399,679 (-126.838%) | 213,073 | 102,036 (32.381%) | 501,715 (70.191%) |
| **Token-weighted aggregate** | **792,912** | **1,463,066** | **-670,154 (-84.518%)** | **682,422** | **110,490 (13.935%)** | **780,644 (53.357%)** |

V8 used fewer parent tokens than v6 in all four settings and fewer than Standard in three. Luna/xhigh was the exception against Standard, using 14.023% more parent tokens.

### Forced Spark efficacy

Each treatment used one exact Spark/medium worker. All eight paired cells passed correctness, and each pair ran sequentially in one source artifact.

| Parent model / effort | No-Spark parent | Spark parent | Parent saved | Spark child | Combined | Spawned / useful | Wall time saved |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `gpt-5.6-sol` / medium | 117,286 | 91,604 | 25,682 (21.897%) | 192,670 | 284,274 | 1 / 1 | 7.556s (12.645%) |
| `gpt-5.6-sol` / high | 100,218 | 131,005 | -30,787 (-30.720%) | 512,620 | 643,625 | 1 / 1 | -12.348s (-15.183%) |
| `gpt-5.6-luna` / xhigh | 251,845 | 95,075 | 156,770 (62.249%) | 368,338 | 463,413 | 1 / 1 | 78.230s (56.270%) |
| `gpt-5.6-luna` / max | 213,073 | 116,126 | 96,947 (45.499%) | 120,155 | 236,281 | 1 / 1 | 94.247s (57.269%) |
| **Aggregate** | **682,422** | **433,810** | **248,612 (36.431%)** | **1,193,783** | **1,627,593** | **4 / 4** | **167.685s (37.709%)** |

The aggregate saved 62,153 parent tokens per spawn. The result is not uniform: SOL/high regressed in both parent tokens and wall time. Combined tokens rose because worker tokens are a separate disclosure rather than the optimized allowance.

### Native auto-routing

The nine-case Luna/xhigh auto arm reduced parent tokens from 1,675,854 to 1,658,999, saving 16,855 (1.006%). Seven workers spawned and six were useful, producing 2,407.857 saved parent tokens per spawn. Child tokens were 828,230 and combined tokens were 2,487,229. All six delegation-required cases spawned, all three forbidden cases stayed local, and all children drained. Because the block used `jobs=4`, wall time is contention-affected and not a speedup measurement.

## Interpretation

- The strongest general v8 result is the no-Spark profile: 13.935% fewer aggregate parent tokens than Standard and 53.357% fewer than frozen v6 on the four-setting migration comparison.
- Forced offload can materially protect the parent allowance and wall time on Luna, but the SOL/high regression prevents a universal Spark claim.
- Native auto-routing saved only 1.006% of parent tokens across nine cases while spawning seven workers. It should remain selective rather than default-on for every parallelizable task.
- Spark child tokens are capacity telemetry. Parent-token savings are not total-cost savings when combined tokens rise.

## Reproduce the verifier

```bash
python3 scripts/verify_v8_release.py \
  --raw benchmarks/results/raw/v8-release-sol-medium-terse-r2.json \
  --raw benchmarks/results/raw/v8-release-sol-high-terse-r2.json \
  --raw benchmarks/results/raw/v8-release-luna-max-terse-r2.json \
  --raw benchmarks/results/raw/v8-release-primary-luna-xhigh-terse-r2.json \
  --raw benchmarks/results/raw/v8-release-v6-luna-xhigh-retry-terse-r2.json \
  --retained-selection benchmarks/results/v8-release-luna-xhigh-selection.json
```

The verifier binds every selected result to the frozen manifest, profile, policy, role, runner, and source hashes before recomputing the tables.

## Limitations

- Each scored cell has one observation; the matrix estimates neither variance nor statistical confidence.
- The terse contract rewrite was informed by excluded gates and pre-rewrite release cells, so the final suite is engineering evidence rather than an untouched holdout study.
- Synthetic local tasks omit organizational context, live users, browser drift, and mutable external services.
- Model decisions, caching, provider errors, and tool selection remain stochastic.
- The isolated Luna/xhigh v6 retry is same-seed but not same-batch; its token comparison may include runtime variance.
- Auto-routing latency is contention-affected. Only the sequential forced pairs support direct wall-time comparisons.
- Harness-forced Spark and native parent-routed Spark measure different mechanisms and must remain separate.
- Parent-token savings do not establish provider billing, allowance, or total-cost savings when combined tokens increase.
- Ten fixtures and one pass per cell are insufficient for production-generalization claims.
