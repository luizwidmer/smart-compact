# Smart Compact

[Smart Compact](https://github.com/luizwidmer/smart-compact) is an experimental Codex profile and skill for reducing parent-model token use while preserving correctness, safety, and exact task constraints.

V8 is the current profile. It uses terse machine-oriented instructions, native Codex compaction, bounded tool history, and optional Spark offload. Parent tokens are the primary objective; Spark and combined tokens are disclosed separately.

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

The installer always installs both versions side by side: CLI profiles `smart-compact-v6` and `smart-compact-v8`, plus skills `$smart-compact-v6` and `$smart-compact-v8`. `--version` only selects the `smart-compact` / `$smart-compact` compatibility alias and default target. The installer is idempotent and preserves differing files unless `--force` is supplied. It also supports `--dry-run`, `--no-spark`, `--no-profile`, `--no-plugin`, and `--make-default`. Restart Codex or open a new task after installation.

## Use

- Selected CLI alias: `codex --profile smart-compact`
- Versioned CLI profiles: `codex --profile smart-compact-v6` or `codex --profile smart-compact-v8`
- Existing task: `$smart-compact`, `$smart-compact-v6`, or `$smart-compact-v8`
- Codex app: select `@Smart Compact`

```text
Use $smart-compact. Minimize parent-model tokens while preserving all requirements and verification.
```

## What v8 changes

- Uses low verbosity, no surfaced reasoning summary, native-default automatic compaction, and a 1,500-token stored tool-output limit.
- Encodes parent, worker, and compaction instructions as terse key-value contracts.
- Batches necessary reads, patches coherently, runs exact acceptance once, and retries only diagnosed failures.
- Gives Spark no fixed worker cap, but selects the smallest useful set and counts every spawn in the efficiency metric.
- Keeps shared decisions, integration, safety-sensitive work, and final acceptance on the parent.

## V8 benchmark snapshot

The release matrix contains 34 single-pass cells over ten hermetic agentic cases. The hard gate is task correctness: all 34 cells passed. A secondary audit recorded 26/34 full-protocol and 33/34 RTK compliance without changing graded outputs. Six earlier tuning cells bring the scored v8 total to 40. V7 was a diagnostic gap and was not rerun.

### Standard to v6 to v8, no Spark

These rows run the same `monorepo-sdk-migration` task. All 12 arm/settings combinations passed correctness.

| Parent model / effort | Standard parent tokens | V6 parent tokens | V6 saved vs Standard | V8 no-Spark parent tokens | V8 saved vs Standard | V8 saved vs v6 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `gpt-5.6-sol` / medium | 125,857 | 193,980 | -68,123 (-54.1%) | 117,286 | 8,571 (6.8%) | 76,694 (39.5%) |
| `gpt-5.6-sol` / high | 131,074 | 206,214 | -75,140 (-57.3%) | 100,218 | 30,856 (23.5%) | 105,996 (51.4%) |
| `gpt-5.6-luna` / xhigh | 220,872 | 348,084 | -127,212 (-57.6%) | 251,845 | -30,973 (-14.0%) | 96,239 (27.6%) |
| `gpt-5.6-luna` / max | 315,109 | 714,788 | -399,679 (-126.8%) | 213,073 | 102,036 (32.4%) | 501,715 (70.2%) |
| **Token-weighted aggregate** | **792,912** | **1,463,066** | **-670,154 (-84.5%)** | **682,422** | **110,490 (13.9%)** | **780,644 (53.4%)** |

V8 beat frozen v6 in every setting and Standard in three of four. The current v6 controls are fresh same-task controls, not the historical calculator totals.

### Forced Spark efficacy

Each forced row used one `gpt-5.3-codex-spark` / medium worker. All eight no-Spark/Spark cells passed correctness. Positive savings mean Spark reduced parent use or wall time; combined tokens include the child.

| Parent model / effort | No-Spark parent | Spark parent | Parent saved | Spark child | Combined | Spawned / useful | Wall time saved |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `gpt-5.6-sol` / medium | 117,286 | 91,604 | 25,682 (21.9%) | 192,670 | 284,274 | 1 / 1 | 7.556s (12.6%) |
| `gpt-5.6-sol` / high | 100,218 | 131,005 | -30,787 (-30.7%) | 512,620 | 643,625 | 1 / 1 | -12.348s (-15.2%) |
| `gpt-5.6-luna` / xhigh | 251,845 | 95,075 | 156,770 (62.2%) | 368,338 | 463,413 | 1 / 1 | 78.230s (56.3%) |
| `gpt-5.6-luna` / max | 213,073 | 116,126 | 96,947 (45.5%) | 120,155 | 236,281 | 1 / 1 | 94.247s (57.3%) |
| **Aggregate** | **682,422** | **433,810** | **248,612 (36.4%)** | **1,193,783** | **1,627,593** | **4 / 4** | **167.685s (37.7%)** |

The aggregate parent saving was 62,153 tokens per spawned worker. Combined tokens increased because Spark uses a separate worker allowance. SOL/high regressed, so Spark is not a universal win.

### Native auto-routing

Across nine `gpt-5.6-luna` / xhigh cases, auto-routing reduced parent tokens from 1,675,854 to 1,658,999: 16,855 saved (1.0%). It spawned seven workers, six useful, for 2,407.857 saved parent tokens per spawn; child tokens were 828,230 and combined tokens were 2,487,229. All six delegation-required cases spawned, all three forbidden cases stayed local, and every child drained. Parallel execution makes wall time diagnostic only.

## Evidence and limitations

The matrix used one observation per cell, seed `20260721`, Codex `0.144.1`, and RTK `0.43.0`. A Luna/xhigh v6 control was selected from an isolated same-seed retry after upstream 503 and stream disconnects exhausted its original 900-second run; the failed attempt is preserved and excluded. Full provenance, hashes, and raw artifacts are in [`RESEARCH.md`](RESEARCH.md).

- Single-pass measurements do not estimate variance or statistical confidence.
- Synthetic local tasks do not represent every production repository or organization.
- Parallel auto-routing latency is contention-affected and is not a speedup claim.
- Parent-token savings are not total-cost savings when combined tokens increase.

## Validate

```bash
python3 scripts/benchmark_v8.py \
  --cases benchmarks/agentic-v8-confirmation.json \
  --validate-fixtures

python3 -m unittest discover -s tests -v
```

The benchmark toolkit, frozen inputs, raw evidence, verifier, and tests live under [`benchmarks/`](benchmarks), [`scripts/`](scripts), and [`tests/`](tests).

## License

Copyright 2026 Luiz Widmer. Licensed under the [Apache License 2.0](LICENSE); see [NOTICE](NOTICE).
