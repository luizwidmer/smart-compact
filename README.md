# Smart Compact

[Smart Compact](https://github.com/luizwidmer/smart-compact) is an experimental Codex profile and skill for reducing parent-model token use while preserving correctness, safety, and exact task constraints.

V7 combines concise native profile settings with conservative, adaptive Spark delegation. Parent tokens are the primary objective. Spark tokens and combined tokens are reported separately.

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/luizwidmer/smart-compact/main/install.sh | sh
```

From a checkout:

```bash
git clone https://github.com/luizwidmer/smart-compact.git
cd smart-compact
./install.sh
```

The installer is idempotent and does not overwrite differing files unless `--force` is supplied. Useful options:

```bash
./install.sh --dry-run
./install.sh --force
./install.sh --no-spark
./install.sh --no-profile
./install.sh --no-plugin
./install.sh --make-default
```

Restart Codex or open a new task after installation.

## Use

- Start the named CLI profile with `codex --profile smart-compact`.
- Invoke the skill in an existing task with `$smart-compact`.
- Select `@Smart Compact` in the Codex app to create a task through the bundled profile picker.

Example:

```text
Use $smart-compact. Minimize parent-model tokens while preserving all requirements and verification.
```

## What v7 changes

- Uses low visible verbosity, no surfaced reasoning summary, a 2,000-token stored tool-output limit, and lossless operational compaction.
- Avoids plans and repeated inspection for bounded tasks with an exact target and acceptance command.
- Batches independent reads and keeps final integration and acceptance on the parent.
- Treats Spark as optional. There is no fixed one-worker cap.
- Chooses the smallest useful worker set; one worker may own several nonoverlapping partitions.
- Adds another worker only for material parent work avoided or critical-path parallelism.
- Keeps tiny, sequential, overlapping, risky, destructive, externally stateful, or unverifiable work local.

## V7 benchmark snapshot

The v7 suite contains ten hermetic agentic cases: six development cases and four held-out cases. The agreed matrix ran four arms once each, for 40 total runs, with six runs executing concurrently. The parent ran `gpt-5.6-luna` at high reasoning; Spark arms used `gpt-5.3-codex-spark` at medium reasoning.

| Comparison | Parent model / effort | Spark model / effort | Baseline parent tokens | Smart Compact v7 parent tokens | Parent tokens saved | Total savings | Correctness |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Standard, no Spark -> v7, no Spark | `gpt-5.6-luna` / high | Disabled | 1,841,804 | 1,223,877 | 617,927 | 33.5% | 9/10 both |
| Frozen v6, Spark -> v7, Spark | `gpt-5.6-luna` / high | `gpt-5.3-codex-spark` / medium | 3,757,550 | 1,537,036 | 2,220,514 | 59.1% | 9/10 both |

These are token-weighted totals across ten runs per arm, matching the presentation used for v6. The less outlier-sensitive paired medians were 59,516.5 parent tokens saved (31.593%) without Spark and 41,894.5 saved (30.153%) against frozen v6 with Spark. Full policy success was 9/10 for v7 without Spark and 4/10 for v7 with Spark because routing evidence is stricter than task correctness.

Against frozen v6 with the same Spark capability, v7 reduced paired median parent tokens by **30.153%** and combined tokens by **17.693%**, with equal task quality. V7 used fewer parent tokens in 8/10 cases.

The strongest parent-token result was v7 without Spark: paired median parent use was 31.593% below the standard no-Spark arm. Enabling Spark on the same v7 profile increased paired median parent use by 10.4755% and combined use by 141.691%, winning parent tokens in only 1/10 cases.

That result makes the release guidance deliberately conservative: the v7 profile is the measured improvement; Spark remains a selectively gated offload mechanism, not a default token-saving claim.

These are single-pass exploratory measurements. The runner requires three trials per cell for confirmatory publication, and parallel execution makes latency non-publishable. See [`RESEARCH.md`](RESEARCH.md) for protocol, provenance, exclusions, and limitations, and [`benchmarks/results/v7-40-summary.json`](benchmarks/results/v7-40-summary.json) for compact per-run evidence.

## Spark behavior

When `spark_worker` is available, Smart Compact may delegate substantial independent mechanical work under these rules:

1. Name nonoverlapping partitions and exclusive inputs or write paths.
2. Count every spawned worker in the efficiency denominator, including failed or redundant workers.
3. Prefer the fewest workers that can replace meaningful parent inspection or editing.
4. Preserve exact shell-wrapper and acceptance constraints in every delegation brief.
5. Do not reread or redo accepted worker work unless integration or acceptance finds a conflict.
6. Keep final decisions, shared edits, integration, and deterministic acceptance on the parent.

If Spark is unavailable, Smart Compact continues locally without substituting another role or probing repeatedly.

## Package contents

| Path | Purpose |
| --- | --- |
| [`SKILL.md`](SKILL.md) | User-invoked Smart Compact policy |
| [`profiles/smart-compact.config.toml`](profiles/smart-compact.config.toml) | Native Codex profile |
| [`.codex/agents/spark-worker.toml`](.codex/agents/spark-worker.toml) | Optional Spark worker definition |
| [`plugin/`](plugin) | Bundled skill and in-app profile picker |
| [`benchmarks/`](benchmarks) | Frozen cases, policies, profiles, freeze metadata, and summary results |
| [`scripts/benchmark_v7.py`](scripts/benchmark_v7.py) | Hermetic four-arm v7 runner and scorer |
| [`RESEARCH.md`](RESEARCH.md) | Detailed methodology and evidence |
| [`tests/`](tests) | Package and benchmark regression tests |

RTK is supported but not bundled. When a workspace requires RTK, Smart Compact preserves the literal wrapper on every command and retry.

## Reproduce and validate

Install the optional benchmark dependency:

```bash
python3 -m pip install -r requirements-benchmark.txt
```

Validate all ten fixtures without model calls:

```bash
python3 scripts/benchmark_v7.py \
  --cases benchmarks/agentic-v7-confirmation.json \
  --validate-fixtures
```

Run the same single-pass 40-cell matrix:

```bash
python3 scripts/benchmark_v7.py \
  --cases benchmarks/agentic-v7-confirmation.json \
  --arm standard-no-spark \
  --arm v6-spark \
  --arm v7-no-spark \
  --arm v7-spark \
  --repetitions 1 \
  --jobs 6 \
  --seed 20260718 \
  --output /path/to/v7-results.json
```

Run package tests:

```bash
python3 -m unittest discover -s tests -v
```

The current suite contains 93 passing regression tests.

## Limitations

- One model run per matrix cell does not estimate variance or statistical confidence.
- Synthetic local tasks do not represent every production repository or organization.
- Token caching, model decisions, and tool selection introduce run-to-run variance.
- Parallel latency is contention-affected and must not be presented as clean speedup.
- Parent-token savings are not total-cost savings unless combined tokens also decline.
- Repeat substantially similar workloads before enabling Spark automatically in production.

## License

Copyright 2026 Luiz Widmer. Licensed under the [Apache License 2.0](LICENSE); see [NOTICE](NOTICE).
