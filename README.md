# Smart Compact

[Smart Compact](https://github.com/luizwidmer/smart-compact) is an experimental Codex profile and skill for reducing parent-model token use while preserving correctness, safety, and exact task constraints.

V8 is the default profile. The experimental optimizer package also installs the frozen v6 compatibility profile and the tested natural-language v8 lane, then recommends a lane before a new task starts. Parent tokens are the primary objective; Spark and combined tokens are disclosed separately.

## Install

Install v8 from GitHub:

```bash
curl -fsSL https://raw.githubusercontent.com/luizwidmer/smart-compact/main/install.sh | sh -s -- --version v8
```

From a checkout:

```bash
git clone https://github.com/luizwidmer/smart-compact.git
cd smart-compact
./install.sh --version v8
```

V6 remains available as the frozen compatibility version:

```bash
./install.sh --version v6
```

The installer keeps `--version v6` and `--version v8` as the alias choices. It installs both frozen versions plus the `smart-compact-v8-natural` optimizer lane side by side. The installer is idempotent and preserves differing files unless `--force` is supplied. It also supports `--dry-run`, `--no-spark`, `--no-profile`, `--no-plugin`, and `--make-default`. Restart Codex or open a new task after installation.

## Use

- Selected CLI alias: `codex --profile smart-compact`
- Versioned CLI profiles: `smart-compact-v6`, `smart-compact-v8`, or `smart-compact-v8-natural`
- Existing task skills: `$smart-compact`, `$smart-compact-v6`, `$smart-compact-v8`, or `$smart-compact-v8-natural`
- Codex app: select `@Smart Compact`

```text
Use $smart-compact. Minimize parent-model tokens while preserving all requirements and verification.
```

For a new task, select the lane from routing mode and task shape:

```bash
python3 scripts/select_optimizer_profile.py \
  --routing-mode auto_spark \
  --task-shape general \
  --format command
```

The command includes a config-level multi-agent toggle, so routing state adds no prompt tokens. The plugin exposes the same read-only recommendation and can create an empty optimized task with the exact bundled profile and routing configuration. Profile selection happens before task creation; it does not change the current task. See [`optimizer/README.md`](optimizer/README.md) for the lane rules and evidence boundary.

## What v8 changes

- Uses low verbosity, no surfaced reasoning summary, native-default automatic compaction, and a 1,500-token stored tool-output limit.
- Encodes parent, worker, and compaction instructions as terse key-value contracts.
- Batches necessary reads, patches coherently, runs exact acceptance once, and retries only diagnosed failures.
- Gives Spark no fixed worker cap, but selects the smallest useful set and counts every spawn in the efficiency metric.
- Keeps shared decisions, integration, safety-sensitive work, and final acceptance on the parent.

## V8 benchmark snapshot

The corrected additive release contains 66 fresh single-pass cells over 12 live cases: the official six-language calculator and Relay Bench website, plus ten newer agentic cases. All 66 passed task correctness and treatment integrity. The release has 24 Standard/v6 controls and 42 v8 cells; six earlier tuning cells bring the release evidence total to 72. V7 remains a diagnostic gap and was not rerun.

### Standard to v6 to v8, no Spark

All 36 Standard/v6/v8 no-Spark cells passed. Negative savings mean the newer arm used more parent tokens.

| Benchmark | Parent / effort | Standard parent | V6 parent | V6 saved vs Standard | V8 no-Spark parent | V8 saved vs Standard | V8 saved vs v6 |
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
| **Token-weighted aggregate** | **All 12 rows** | **3,138,482** | **3,361,104** | **-222,622 (-7.1%)** | **3,004,930** | **133,552 (4.3%)** | **356,174 (10.6%)** |

Across the three anchors, v8 no-Spark used 4.3% fewer parent tokens than Standard and 10.6% fewer than frozen v6. Results varied materially by task and setting, so the aggregate is not a universal per-task claim.

### Forced Spark efficacy

All 24 paired no-Spark/forced-Spark cells passed task correctness. Each forced cell spawned one useful `gpt-5.3-codex-spark` / medium worker.

| Benchmark | No-Spark parent | Forced-Spark parent | Parent saved | Spawned / useful | Saved per spawn | Spark child | Combined |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Calculator | 1,344,384 | 1,180,003 | 164,381 (12.2%) | 4 / 4 | 41,095 | 3,140,401 | 4,320,404 |
| Relay Bench | 971,495 | 287,321 | 684,174 (70.4%) | 4 / 4 | 171,044 | 1,040,196 | 1,327,517 |
| Migration | 689,051 | 421,558 | 267,493 (38.8%) | 4 / 4 | 66,873 | 1,312,213 | 1,733,771 |
| **Aggregate** | **3,004,930** | **1,888,882** | **1,116,048 (37.1%)** | **12 / 12** | **93,004** | **5,492,810** | **7,381,692** |

Forced Spark reduced the parent allowance in aggregate, while combined tokens increased. Child tokens are capacity telemetry, not the primary objective.

### Native auto-routing

Across nine Luna/xhigh cases, auto-routing reduced parent tokens from 1,504,871 to 1,348,648: 156,223 saved (10.4%). It spawned six workers, five useful, for 26,037 saved parent tokens per spawn. All six required cases spawned, all three forbidden cases stayed local, and every child drained. One child-usage record was incomplete, so the full child and combined totals are intentionally null; 420,953 child tokens were observed from the other eight cells.

## Evidence and limitations

The release used one observation per cell, seed `20260721`, Codex `0.144.1`, and RTK `0.43.0`. All 66 cells were fresh; no retained release selection was used. Protocol compliance was 58/66, scope compliance 65/66, usage completeness 65/66, and RTK compliance 66/66. These secondary misses did not change graded task correctness or treatment integrity.

- Single-pass measurements do not estimate variance or statistical confidence.
- Synthetic local tasks do not represent every production repository or organization.
- Parallel execution makes release wall time nonpublishable.
- Parent-token savings are not total-cost savings when combined tokens increase.

A separate 42-cell verbose natural-language sensitivity experiment is documented in [`RESEARCH.md`](RESEARCH.md). It is not pooled into the 66-cell release; its exact treatment is now installed as the optional natural lane while terse v8 remains the default.

## Validate

```bash
python3 scripts/benchmark_v8.py \
  --cases benchmarks/agentic-v8-confirmation.json \
  --validate-fixtures

python3 scripts/verify_optimizer_package.py

python3 -m unittest discover -s tests -v
```

The benchmark toolkit, frozen inputs, raw evidence, verifier, and tests live under [`benchmarks/`](benchmarks), [`scripts/`](scripts), and [`tests/`](tests).

## License

Copyright 2026 Luiz Widmer. Licensed under the [Apache License 2.0](LICENSE); see [NOTICE](NOTICE).
