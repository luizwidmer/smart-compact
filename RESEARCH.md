# Real-World Agentic Benchmark Research

Research snapshot: 2026-07-15.

## Scope and claim boundary

Smart Compact V9 is the sole current product generation. V6, V7, and V8 remain immutable benchmark history; the new real-world cases add to the official legacy benchmarks rather than replacing them.

The primary objective is parent-model token reduction. Task correctness, safety, allowed scope, and routing treatment are gates. Spark child tokens are telemetry, not the optimized allowance. Wall time is diagnostic because runs were parallel and contended.

The suite uses local, hermetic, resettable workspaces with deterministic graders. It borrows evaluation patterns from [SWE-bench](https://github.com/SWE-bench/SWE-bench), [Terminal-Bench](https://www.tbench.ai/benchmarks/terminal-bench-2), [WorkArena](https://github.com/ServiceNow/WorkArena), [TheAgentCompany](https://github.com/TheAgentCompany/TheAgentCompany), [tau-bench](https://arxiv.org/abs/2406.12045), and [OSWorld](https://arxiv.org/abs/2404.07972). It does not reproduce those datasets or claim comparable leaderboard scores.

## State is an optimization cost

The official V9 candidate first enforced the same minimal-local state everywhere except implementation, where it attempted Spark. All 12 tasks were correct, but that uniform policy used 3,817,102 parent tokens:

| Policy | Parent tokens | Effect versus definitive V9 |
| --- | ---: | ---: |
| Uniform enforced V9 state | 3,817,102 | 1,209,336 more |
| Definitive state-aware V9 | 2,607,766 | 1,209,336 saved (31.682%) |

The uniform candidate also used more parent tokens than Standard (3,138,482), V6 (3,361,104), and V8 (3,004,930). A short instruction state is therefore not automatically free: its behavior can add parent work or displace a better native or historical treatment. The result does not isolate prompt bytes as the sole causal mechanism, but it is sufficient to reject universal state enforcement for this package.

The definitive V9 optimizer treats the state as part of the intervention and selects it before inference.

## Definitive V9 package

| Lane | State | Multi-agent | Role |
| --- | --- | --- | --- |
| `native` | No profile instructions | Disabled | Zero added instruction state |
| `v9-v8` | Byte-identical frozen v8-compatible profile under a V9-only ID | Disabled | Preserve measured v8 strengths without restoring V8 as a product |
| `v9` | 259-byte minimal local contract | Disabled | Current local workflow and conservative fallback |
| `v9-spark` | 769-byte explicit offload contract | Enabled | Measured Luna/max implementation win |

V6's useful workflow constraints are folded into the minimal V9 contract. Direct V6 benchmark rows remain controls because their treatment included a separate skill input and cannot be reproduced exactly as a profile-only lane. The v8-compatible lane is exact and deployable, so it can be selected without relabeling a new approximation as V8 evidence.

Selection uses four dimensions: routing mode, task shape, model family, and effort. Unknown settings take the minimal local fallback rather than assuming a measured win.

### Official routing

| Benchmark / task shape | Sol / medium | Sol / high | Luna / xhigh | Luna / max |
| --- | --- | --- | --- | --- |
| Calculator / implementation | `v9-v8` | `v9-v8` | `v9-v8` | `v9-spark` under `auto_spark`; otherwise `v9-v8` |
| Relay / handoff | `v9` | `v9` | `v9` | `v9-v8` |
| SDK Migration / migration | `native` | `v9-v8` | `v9-v8` | `v9-v8` |

### Fresh-addition routing

| Case shape | Model / effort | Selected lane |
| --- | --- | --- |
| Implementation | Sol / medium | `v9-v8` |
| Migration | Sol / high | `v9-v8` |
| Handoff | Luna / xhigh | `v9` |
| General | Luna / max | `v9` |

## Official legacy benchmark results

| Benchmark | Model / effort | Standard | V6 | V8 | V9 parent | Lane |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| Calculator | Sol / medium | 448,551 | 147,287 | 114,812 | 114,812 | `v9-v8` |
| Calculator | Sol / high | 293,003 | 173,915 | 271,642 | 271,642 | `v9-v8` |
| Calculator | Luna / xhigh | 420,095 | 336,471 | 409,852 | 409,852 | `v9-v8` |
| Calculator | Luna / max | 559,838 | 655,352 | 548,078 | 463,836 | `v9-spark` |
| Relay | Sol / medium | 156,702 | 163,259 | 168,563 | 138,871 | `v9` |
| Relay | Sol / high | 140,322 | 138,970 | 179,239 | 115,276 | `v9` |
| Relay | Luna / xhigh | 251,921 | 499,673 | 483,667 | 281,655 | `v9` |
| Relay | Luna / max | 156,912 | 163,112 | 140,026 | 140,026 | `v9-v8` |
| SDK Migration | Sol / medium | 114,900 | 101,684 | 132,155 | 114,900 | `native` |
| SDK Migration | Sol / high | 116,482 | 229,494 | 136,167 | 136,167 | `v9-v8` |
| SDK Migration | Luna / xhigh | 248,170 | 561,434 | 203,151 | 203,151 | `v9-v8` |
| SDK Migration | Luna / max | 231,586 | 190,453 | 217,578 | 217,578 | `v9-v8` |
| **Total** | **2 models / 4 efforts** | **3,138,482** | **3,361,104** | **3,004,930** | **2,607,766** | **Hybrid V9** |

V9 saved 530,716 parent tokens (16.910%) versus Standard, 753,338 (22.413%) versus V6, and 397,164 (13.217%) versus V8. All 12 selected official cells were task-correct.

Only the Luna/max Calculator selection used Spark. It spawned one worker, used 463,836 parent tokens versus the v8 lane's 548,078, and reported 273,944 child tokens. The worker count and child usage are telemetry; the optimized budget and release comparison remain parent tokens. The 397,164 aggregate official saving versus V8 per one selected worker is a package-level ratio, not a causal Spark-only saving.

## Fresh real-world additions

The four additions cover multi-provider webhook implementation, service-policy migration, inventory handoff, and formula-safe export work.

| Setting | Shape / lane | V6 parent | V8 parent | V9 parent |
| --- | --- | ---: | ---: | ---: |
| Sol / medium | Implementation / `v9-v8` | 213,796 | 125,211 | 125,211 |
| Sol / high | Migration / `v9-v8` | 297,185 | 106,822 | 106,822 |
| Luna / xhigh | Handoff / `v9` | 122,235 | 92,349 | 123,285 |
| Luna / max | General / `v9` | 396,708 | 144,199 | 107,583 |
| **Total** | **Four additions** | **1,029,924** | **468,581** | **462,901** |

V9 saved 5,680 parent tokens (1.212%) versus V8 on the additions. Across all 16 official and added cases, V9 used 3,070,667 parent tokens versus V8's 3,473,511 and V6's 4,391,028: savings of 402,844 (11.598%) and 1,320,361 (30.070%), respectively. All 16 selected source cells were task-correct.

## Execution integrity and evidence status

The original official V9 runner keyed parallel workspaces too coarsely. Three cells reached real inference; nine collided before inference and recorded `FileExistsError` non-attempts. A separately frozen recovery selected exactly those nine cells and used unique per-cell roots. The combined official evidence is therefore 3 original real cells plus 9 recovery real cells, with zero repeated inference cells.

One recovery Calculator Luna/xhigh cell used raw shell commands without the required RTK wrapper. Its task still scored 240/240 with correct scope, acceptance, and usage. It is disclosed as a nonblocking protocol-only miss rather than treated as a correctness failure.

The four source Spark cells also recorded ephemeral child-read completion telemetry misses. Per-cell app-server cleanup still ran, every task remained correct, and only the Luna/max cell is selected by the definitive router.

The definitive route was chosen after observing deployable native, V8-compatible, minimal-V9, and Spark treatments. Its evidence label is:

```text
post_matrix_deployable_hybrid_selection_not_blinded_confirmation
```

This is verified package-selection evidence, not a new blinded confirmation run. The uniform V9 candidate is retained as a rejected state-cost result rather than hidden.

## Provenance

| Artifact | Role | SHA-256 |
| --- | --- | --- |
| [`benchmarks/results/v9-definitive-summary.json`](benchmarks/results/v9-definitive-summary.json) | Verified 16-cell selection and published metrics | `139e86569c968d88ab340456a19c9413c6cb606c38c2b6e29686a5945f24c9e3` |
| [`benchmarks/v9-official-freeze.json`](benchmarks/v9-official-freeze.json) | Original 12-cell V9 freeze | `6e8a776660a4cf6b5dbd29c2ce0ff0595263712d050c0c3107951a14c78338e6` |
| [`benchmarks/results/raw/v9-official-release.json`](benchmarks/results/raw/v9-official-release.json) | Three real cells plus nine collision non-attempts | `690bbb1ac05220068e87fb92501a3f76d2f2d03c33d473bcdd4ed728ee6ca8d3` |
| [`benchmarks/v9-official-recovery-freeze.json`](benchmarks/v9-official-recovery-freeze.json) | Exact nine-cell recovery freeze | `1229b66d3f2219e8eec67b0068e8a60a484fca600de5f8d5a3952a1131c0d376` |
| [`benchmarks/results/raw/v9-official-recovery.json`](benchmarks/results/raw/v9-official-recovery.json) | Nine recovered real cells | `338a974e4f8327fb428cc4ad4d542122d4345240b994b4769a72cdb3e094d7aa` |
| [`benchmarks/results/raw/v9-final-release.json`](benchmarks/results/raw/v9-final-release.json) | Fresh one-pass 14-cell source matrix | `72729e6f2fc2ca9154a6691fc71cadc35905a56218f509c2cd548ada88d1b431` |
| [`benchmarks/experiments/v9-official-state-routed-rejected/artifacts/optimizer/selection.json`](benchmarks/experiments/v9-official-state-routed-rejected/artifacts/optimizer/selection.json) | Exact pre-run selector snapshot superseded by the definitive router | `afcc9e03b616f2c884c2c04c6b2cb05ac9dbedeb2f4de7194f01d582df7df787` |
| [`benchmarks/results/v8-release-summary.json`](benchmarks/results/v8-release-summary.json) | Frozen Standard, V6, and V8 controls | `f22d5279bca68749e2794935467db4340e1735c7247d98bf992e8d2c29986430` |
| [`optimizer/selection.json`](optimizer/selection.json) | Executable rules and bound source/profile hashes | Verified by `scripts/verify_optimizer_package.py` |

The definitive summary independently recomputes the official, fresh, combined, correctness, worker, and state-cost fields from frozen source artifacts.

## Limitations

- One observation per inference cell provides no variance or confidence interval.
- The route was selected after observing the matrices; it is not blinded confirmation.
- Synthetic repositories omit organizational context, live users, browser drift, and mutable services.
- Model behavior, caching, tool choice, and provider conditions remain stochastic.
- Parallel execution makes wall-time comparisons diagnostic only.
- Parent-token savings are not total-compute savings when Spark child tokens increase combined usage.
- The `native` lane adds no V9 profile but inherits user-owned global Codex configuration; exact Standard-control parity assumes no globally promoted Smart Compact state.
