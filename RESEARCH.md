# Real-World Agentic Benchmark Research

Research snapshot: 2026-07-15.

## Scope

Smart Compact is evaluated on local, hermetic, resettable tasks with deterministic graders. The suite borrows evaluation patterns from established agent benchmarks, but it does not reproduce their datasets or claim comparable leaderboard scores. Every task remains solvable by the parent without Spark.

The primary objective is parent-model token reduction. Task correctness, treatment integrity, safety, and allowed scope are gates. Spark child tokens and combined tokens are disclosed, but Spark runs on a separate allowance and is not the optimized budget. When parent savings are similar, lower wall time and fewer spawned workers are preferred.

## Research influences

| Source | Pattern borrowed | Boundary |
| --- | --- | --- |
| [SWE-bench](https://github.com/SWE-bench/SWE-bench) and [SWE-bench Verified](https://openai.com/index/introducing-swe-bench-verified/) | Repository changes graded by hidden regression tests | Local synthetic repositories are not SWE-bench instances. |
| [SWE-Lancer](https://openai.com/index/swe-lancer/) | End-to-end bug-fix and feature acceptance | No economic-value equivalence is claimed. |
| [Terminal-Bench 2.0](https://www.tbench.ai/benchmarks/terminal-bench-2) | Realistic terminal work in isolated environments | Task shapes, not tasks or scores, are borrowed. |
| [WorkArena](https://github.com/ServiceNow/WorkArena) | Compositional retrieval and knowledge work | The suite does not reproduce ServiceNow or browser interaction. |
| [TheAgentCompany](https://github.com/TheAgentCompany/TheAgentCompany) | Initialized workplaces, state, evaluators, and partial checks | The suite omits its multi-service company simulation. |
| [tau-bench](https://arxiv.org/abs/2406.12045) | Policy-bound stateful workflows and final-state grading | Reference actions are not treated as the only valid implementation path. |
| [OSWorld](https://arxiv.org/abs/2404.07972) | Long workflows, artifact checks, and safety auditing | No OSWorld score equivalence is claimed. |
| [METR Time Horizons](https://metr.org/time-horizons/) | Success and runtime as separate evidence | This single-pass suite cannot support a time-horizon claim. |

## Additive benchmark universe

The corrected v8 release restores both official legacy live benchmarks and adds the ten newer agentic cases. The older tasks are additions to the current suite, not historical totals pooled with new runs.

| Case | Split | Task shape | Native auto-routing expectation |
| --- | --- | --- | --- |
| `legacy-calculator` | Official legacy | Six-language calculator implementation | Forced anchor only |
| `legacy-relay-bench` | Official legacy | Relay Bench website implementation | Forced anchor only |
| `release-readiness` | Development | Repository release reconciliation | Stay local |
| `incident-triage` | Development | Independent incident evidence shards | Delegate |
| `monorepo-sdk-migration` | Development | Path-disjoint multi-package migration | Forced anchor only |
| `offline-advisory-triage` | Development | Offline dependency-security workflow | Delegate |
| `ci-matrix-root-cause` | Held-out | Multi-platform CI diagnosis | Delegate |
| `tenant-config-drift` | Held-out | Configuration reconciliation | Delegate |
| `support-credit-adjudication` | Held-out | Evidence-based back-office workflow | Delegate |
| `permission-scope-regression` | Held-out | Sequential permission-boundary repair | Stay local |
| `multi-service-contract-rollout` | Held-out | Multi-service API migration | Delegate |
| `policy-bound-batch-update` | Held-out | Stateful policy workflow | Stay local |

Each fixture has a clean seed, deterministic reset, user specification, hidden outcome checks, an oracle used only to validate the fixture, allowed-path constraints, and no required external network service.

## Frozen treatments and matrix

V6 is the exact preserved harness profile and policy, not a reconstruction. V7 is retained as diagnostic history but was not rerun; the fresh comparison is Standard versus v6 versus v8.

The four parent settings are `gpt-5.6-sol` medium/high and `gpt-5.6-luna` xhigh/max. Spark is `gpt-5.3-codex-spark` at medium effort. Seed `20260721` and one observation per cell are fixed.

| Arm | Cells | Coverage |
| --- | ---: | --- |
| `standard-no-spark` | 12 | Three anchors at four settings |
| `v6-no-spark` | 12 | Same anchors and settings |
| `v8-no-spark` | 21 | Three anchors at four settings plus nine non-anchor cases |
| `v8-spark-forced` | 12 | Three anchors at four settings |
| `v8-spark-auto` | 9 | Nine non-anchor cases at Luna/xhigh |
| **Fresh release** | **66** | **24 controls and 42 v8 candidates** |

Six pre-release tuning cells are kept outside the release verifier, making 72 total evidence cells. The seven-case offline compact-guard suite is separate and non-inference.

Important frozen hashes:

| Artifact | SHA-256 |
| --- | --- |
| [`profiles/smart-compact-v8.config.toml`](profiles/smart-compact-v8.config.toml) | `b3e4658e957811c69640351cb2302b759ff0a1811bc83fab5b08dbbf63a4e48c` |
| [`benchmarks/policies/v8/SKILL.md`](benchmarks/policies/v8/SKILL.md) | `44fbe5838731fa6d25af293a780557bf1e32a93dd5eb5de0e45b6b1a1dcaf327` |
| [`.codex/agents/spark-worker.toml`](.codex/agents/spark-worker.toml) | `ac0aaa80e9a8a5ee4c7a7d83cc048af69d44ac6856103734b2c3ff3505af0c68` |
| [`benchmarks/profiles/v6.config.toml`](benchmarks/profiles/v6.config.toml) | `2efbedb6ff202b724bea6245d97136e6db9d044524eaf0b8ea0c3495df4d3ff7` |
| [`benchmarks/policies/v6/SKILL.md`](benchmarks/policies/v6/SKILL.md) | `263c3d72c00897509bf04ffe5a98d1333c8a087a03b6091d55b2267df18e416f` |
| [`benchmarks/agentic-v8-confirmation.json`](benchmarks/agentic-v8-confirmation.json) | `968c222cf82c41b77ce1bbc37b0cc426ae4cd5a4139c83690abc81d0b434d534` |
| [`benchmarks/agentic-v8-legacy-calculator.json`](benchmarks/agentic-v8-legacy-calculator.json) | `4ed252fb96a745b7ffca39a66667af470b1d0a003a651f65d0c13a22cd017218` |
| [`benchmarks/agentic-v8-legacy-relay-bench.json`](benchmarks/agentic-v8-legacy-relay-bench.json) | `082608b014ee12dbb771ef12d82842b1b3511068c9c51bd684a6e02fdc49e30a` |
| [`scripts/benchmark_v8.py`](scripts/benchmark_v8.py) | `1467b98202d74782659d68de2ba1d26cd970ce11858875f52f5e4ab52ac3b5ea` |
| [`scripts/verify_v8_release.py`](scripts/verify_v8_release.py) | `53f6c9079f5e9ce110a5bf9603c82b0ea6b7ade79a60f6f7bfb72f04fa884866` |

The exact freeze is [`benchmarks/v8-freeze.json`](benchmarks/v8-freeze.json). Relay validation was refrozen before its accepted rerun to remove implementation-specific spellings while preserving behavioral, accessibility, visual, and safety requirements. Earlier Relay attempts are preserved but excluded. After inference, the verifier was corrected to apply the already-declared task-correctness gate and to represent missing child usage as incomplete rather than zero; no task, treatment, raw token value, or model setting changed.

## Release acceptance

All 66 cells passed graded task correctness and treatment integrity. Secondary diagnostics were 58/66 protocol-compliant, 66/66 RTK-compliant, 65/66 scope-compliant, and 65/66 usage-complete. The scope miss and protocol-only misses did not change task output. One `offline-advisory-triage` auto child lacked final usage telemetry; the parent usage is valid, child totals are nullable, and the event is not misreported as zero.

### Standard to v6 to v8, no Spark

All 36 cells in this comparison passed task correctness. Negative savings mean the newer arm used more parent tokens.

| Benchmark | Parent / effort | Standard | V6 | V6 saved vs Standard | V8 no-Spark | V8 saved vs Standard | V8 saved vs v6 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Calculator | SOL / medium | 448,551 | 147,287 | 301,264 (67.2%) | 114,812 | 333,739 (74.4%) | 32,475 (22.0%) |
| Calculator | SOL / high | 293,003 | 173,915 | 119,088 (40.6%) | 271,642 | 21,361 (7.3%) | -97,727 (-56.2%) |
| Calculator | Luna / xhigh | 420,095 | 336,471 | 83,624 (19.9%) | 409,852 | 10,243 (2.4%) | -73,381 (-21.8%) |
| Calculator | Luna / max | 559,838 | 655,352 | -95,514 (-17.1%) | 548,078 | 11,760 (2.1%) | 107,274 (16.4%) |
| Relay Bench | SOL / medium | 156,702 | 163,259 | -6,557 (-4.2%) | 168,563 | -11,861 (-7.6%) | -5,304 (-3.2%) |
| Relay Bench | SOL / high | 140,322 | 138,970 | 1,352 (1.0%) | 179,239 | -38,917 (-27.7%) | -40,269 (-29.0%) |
| Relay Bench | Luna / xhigh | 251,921 | 499,673 | -247,752 (-98.3%) | 483,667 | -231,746 (-92.0%) | 16,006 (3.2%) |
| Relay Bench | Luna / max | 156,912 | 163,112 | -6,200 (-4.0%) | 140,026 | 16,886 (10.8%) | 23,086 (14.2%) |
| Migration | SOL / medium | 114,900 | 101,684 | 13,216 (11.5%) | 132,155 | -17,255 (-15.0%) | -30,471 (-30.0%) |
| Migration | SOL / high | 116,482 | 229,494 | -113,012 (-97.0%) | 136,167 | -19,685 (-16.9%) | 93,327 (40.7%) |
| Migration | Luna / xhigh | 248,170 | 561,434 | -313,264 (-126.2%) | 203,151 | 45,019 (18.1%) | 358,283 (63.8%) |
| Migration | Luna / max | 231,586 | 190,453 | 41,133 (17.8%) | 217,578 | 14,008 (6.0%) | -27,125 (-14.2%) |
| **Token-weighted aggregate** | **All rows** | **3,138,482** | **3,361,104** | **-222,622 (-7.1%)** | **3,004,930** | **133,552 (4.3%)** | **356,174 (10.6%)** |

V8 no-Spark used 4.255% fewer parent tokens than Standard and 10.597% fewer than frozen v6 across the three anchors. Variation by task and model is large; this aggregate is not a universal per-task claim.

### Forced Spark efficacy

Each cell used one exact Spark/medium worker. This was an observed outcome, not a configured one-worker cap. All 12 workers were useful and all 24 paired cells passed correctness.

| Benchmark | Parent / effort | No-Spark parent | Forced parent | Parent saved | Child | Combined |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Calculator | SOL / medium | 114,812 | 207,799 | -92,987 (-81.0%) | 301,148 | 508,947 |
| Calculator | SOL / high | 271,642 | 134,041 | 137,601 (50.7%) | 342,456 | 476,497 |
| Calculator | Luna / xhigh | 409,852 | 228,488 | 181,364 (44.3%) | 2,178,491 | 2,406,979 |
| Calculator | Luna / max | 548,078 | 609,675 | -61,597 (-11.2%) | 318,306 | 927,981 |
| Relay Bench | SOL / medium | 168,563 | 54,636 | 113,927 (67.6%) | 121,504 | 176,140 |
| Relay Bench | SOL / high | 179,239 | 55,078 | 124,161 (69.3%) | 280,393 | 335,471 |
| Relay Bench | Luna / xhigh | 483,667 | 117,607 | 366,060 (75.7%) | 485,145 | 602,752 |
| Relay Bench | Luna / max | 140,026 | 60,000 | 80,026 (57.2%) | 153,154 | 213,154 |
| Migration | SOL / medium | 132,155 | 109,036 | 23,119 (17.5%) | 314,420 | 423,456 |
| Migration | SOL / high | 136,167 | 107,924 | 28,243 (20.7%) | 350,591 | 458,515 |
| Migration | Luna / xhigh | 203,151 | 110,377 | 92,774 (45.7%) | 520,296 | 630,673 |
| Migration | Luna / max | 217,578 | 94,221 | 123,357 (56.7%) | 126,906 | 221,127 |
| **Aggregate** | **12 pairs** | **3,004,930** | **1,888,882** | **1,116,048 (37.1%)** | **5,492,810** | **7,381,692** |

The aggregate saved 93,004 parent tokens per spawned worker. Calculator SOL/medium and Luna/max regressed, so forced Spark is not universally beneficial. Combined tokens increased because worker tokens are separate capacity telemetry.

### Native auto-routing

The nine non-anchor Luna/xhigh pairs reduced parent tokens from 1,504,871 to 1,348,648: 156,223 saved (10.381%). Six workers spawned, five were useful, yielding 26,037 parent tokens saved per spawn. All six delegation-required cases spawned, all three forbidden cases stayed local, and all children drained. Observed child tokens were 420,953, but exact child and combined totals are null because one child usage record was incomplete.

Wall time is not published: the release used parallel, separately contended processes. It is retained only as diagnostic evidence.

## Post-release verbose v8 sensitivity

After the release matrix, v8 was rerun for the same 42 candidate arms with natural-language parent instructions in place of the terse machine contract. Standard and v6 were intentionally not repeated. The profile, compact prompt, automatic-compaction default, 1,500-token tool history, routing modes, Spark worker, tasks, models, efforts, seed, and single-pass design stayed fixed. `skill_input=false`; the frozen verbose `SKILL.md` is an auditable semantic mirror of the actual `developer_instructions` treatment.

| Same v8 arm | Cells | Mechy parent | Verbose parent | Parent saved by verbose | Verbose workers | Verbose child | Verbose combined |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| No-Spark | 21 | 4,509,801 | 3,887,845 | 621,956 (13.791%) | 0 / 0 useful | 0 | 3,887,845 |
| Forced Spark | 12 | 1,888,882 | 1,390,994 | 497,888 (26.359%) | 12 / 12 useful | 3,964,937 | 5,355,931 |
| Auto Spark | 9 | 1,348,648 | 1,439,236 | -90,588 (-6.717%) | 6 / 6 useful | 473,256 | 1,912,492 |
| **All v8 arms** | **42** | **7,747,331** | **6,718,075** | **1,029,256 (13.285%)** | **18 / 18 useful** | **4,438,193** | **11,156,268** |

All 42 accepted verbose cells passed task correctness and treatment integrity. Scope passed 42/42, usage was complete 42/42, and protocol passed 36/42; the six misses were forced-Spark protocol details that did not change graded task output.

Within the verbose treatment, forced Spark reduced the matching anchor no-Spark parent total from 2,681,527 to 1,390,994: 1,290,533 saved (48.127%), or 107,544 per spawn. In contrast, verbose auto-routing increased its matching nine-case no-Spark total from 1,206,318 to 1,439,236: 232,918 more parent tokens (19.308%), or -38,820 per spawn. The sensitivity result therefore supports the natural-language forced-offload contract, but not its auto-routing behavior.

The verbose run produced 45 cell observations for 42 accepted cells. A calculator Luna/max forced attempt failed task correctness and was replaced by one targeted retry. A migration SOL/medium forced attempt failed in an interrupted artifact and was replaced by one targeted retry. A Relay Luna/max pass was preserved in an incomplete checkpoint and rerun once solely to obtain complete top-level provenance. All attempts remain in `benchmarks/results/raw/v8-verbose/`; none is averaged. The verifier binds 16 complete source artifacts and explicitly excludes the complete failed calculator attempt.

This experiment is exploratory. It has no fresh Standard/v6 controls, one observation per cell, possible provider drift, and contention-affected wall time. It is not pooled into the release. Its exact treatment is packaged as an optional optimizer lane; terse v8 remains the alias default.

## Post-release optimization package

Two frozen static hybrids were first tested on the worst verbose-auto cell, `multi-service-contract-rollout` at Luna/xhigh. Both completed the task correctly but failed promotion:

| Candidate | Paired no-Spark parent | Auto parent | Parent saved | Workers | Promotion result |
| --- | ---: | ---: | ---: | ---: | --- |
| Hybrid R1 | 185,029 | 175,377 | 9,652 (5.216%) | 1 useful | Rejected: 1,887 tokens above the prior terse-auto result |
| Hybrid R2 | 198,562 | 193,974 | 4,588 (2.311%) | 1 useful | Rejected: still spawned and regressed further |

The misses were protocol diagnostics, not task-correctness failures. R1 used 39,426 Spark child tokens; R2 used 27,598. Their frozen inputs and raw outputs remain under [`benchmarks/experiments/`](benchmarks/experiments) and [`benchmarks/results/raw/`](benchmarks/results/raw), but neither became an installed profile.

| Target artifact | SHA-256 |
| --- | --- |
| [`v9-candidate-target-multi-service-luna-xhigh.json`](benchmarks/results/raw/v9-candidate-target-multi-service-luna-xhigh.json) | `19638988a0afa69c3ac3c4023dc5aa926de90bbc9676b8a5d479ff3d5b357115` |
| [`v9-candidate-r2-target-multi-service-luna-xhigh.json`](benchmarks/results/raw/v9-candidate-r2-target-multi-service-luna-xhigh.json) | `008cb936ead2743bd24bc52dc88c849bfa22fc9df21847c5adabab62eec816a5` |

The resulting experimental package uses executable conditional lane selection instead of another static blend:

- terse v8 for automatic routing, where natural v8 used 90,588 more parent tokens across nine cells;
- frozen v6 for the four-setting no-Spark implementation aggregate, where it used 31,359 fewer parent tokens than terse v8;
- natural v8 for the remaining 17 no-Spark cells, where it used 1,048,078 fewer parent tokens than terse v8.

No-Spark and production auto-Spark use a pre-inference `multi_agent` configuration toggle, which adds no prompt tokens. The historical auto arm also injected a Spark-availability instruction, so it informs the terse-lane direction but is excluded from the package replay. Forced Spark stays benchmark-only because its harness-supplied handoff cannot be reproduced by a profile without adding instructions or changing the treatment.

The machine-readable rules live in [`optimizer/selection.json`](optimizer/selection.json). A counterfactual replay over the existing 21 no-Spark cells selects 3,430,364 parent tokens versus 4,509,801 for all-terse v8, a difference of 1,079,437 (23.935%). This replay is explicitly not fresh inference or a release claim; it is a development estimate used to choose the next held-out validation matrix.

Frozen verbose treatment hashes:

| Artifact | SHA-256 |
| --- | --- |
| [`benchmarks/experiments/v8-verbose/profile.config.toml`](benchmarks/experiments/v8-verbose/profile.config.toml) | `478e54b0969bfdef2bd87a9e7ff7bca70d41144813043e17b5af4decec584717` |
| [`benchmarks/experiments/v8-verbose/SKILL.md`](benchmarks/experiments/v8-verbose/SKILL.md) | `ccf2cf696a3c6f8da2b26d66281d240212752c0b072a8f81ae2a6f3f8dde3880` |
| [`scripts/benchmark_v8_verbose.py`](scripts/benchmark_v8_verbose.py) | `a158ab20c3dfad95b9b41bb0c8755e5b78c47b46a8a0350c478886081bfffdac` |

The complete verbose freeze is [`benchmarks/experiments/v8-verbose/freeze.json`](benchmarks/experiments/v8-verbose/freeze.json), and the verified comparison is [`benchmarks/results/v8-verbose-comparison.json`](benchmarks/results/v8-verbose-comparison.json).

## Raw provenance

The corrected release verifier binds 13 fresh artifacts: four calculator files under `v8-full-r3-calculator-*`, four migration files under `v8-full-r3-migration-*`, the 18-cell `v8-full-r4-primary-luna-xhigh.json`, and four accepted Relay files under `v8-full-r6-relay-*`. Exact paths, selected cells, manifest hashes, and artifact SHA-256 values are embedded in [`benchmarks/results/v8-release-summary.json`](benchmarks/results/v8-release-summary.json). Earlier `r3` through `r5` Relay artifacts and interrupted primary artifacts are preserved for audit but excluded.

The verbose verifier binds 16 complete artifacts recorded in `provenance.verbose_sources` in the comparison JSON. Incomplete checkpoints are preserved alongside them but cannot satisfy binding metadata and are not silently treated as accepted sources.

Both published JSON summaries were independently regenerated from their explicit source lists and byte-compared with the committed files.

## Offline and implementation verification

- Seven-case compact guard: 487 source tokens to 376 candidate tokens, 111 saved (22.8%), zero failures.
- Fixture validators: official calculator, official Relay Bench, and all ten agentic cases passed seed/oracle/reset/scope checks.
- Policy safety signals: frozen v6, terse v8, and verbose v8 each score 6/6.
- Python suite: 179 tests pass.
- Release verifier: 66/66 cells, `verified: true`.
- Verbose verifier: 42/42 accepted cells, `verified: true`.

## Limitations

- One observation per cell provides no variance or confidence interval.
- Selection and contract tuning make this engineering evidence, not an untouched holdout study.
- Synthetic local tasks omit organizational context, live users, browser drift, and mutable external services.
- Model behavior, caching, provider errors, and tool selection remain stochastic.
- Parallel contention makes wall-time comparisons nonpublishable here.
- Harness-forced Spark and native parent-routed Spark measure different mechanisms.
- Parent-token savings do not establish provider billing or total-cost savings when combined tokens rise.
