# Smart Compact

[Smart Compact](https://github.com/luizwidmer/smart-compact) is an experimental Codex skill for reducing communication and context usage without weakening correctness or safety. Its promoted adaptive policy combines concise handoffs with economical tool use: batch independent work, avoid unnecessary plans, verify acceptance criteria once, rerun only affected failures, and stop when the result is proven.

## Status

Version `v2-adaptive` is the promoted policy in [`SKILL.md`](SKILL.md). It remains a standalone development repository and is not installed globally. The technical skill identifier remains `codex-compact`, preserving `$codex-compact` compatibility while the project and UI use the Smart Compact brand.

## Measured result

The strongest controlled result came from a six-language calculator task covering Python, Rust, C++, Swift, JavaScript, and TypeScript. Only the new Compact arm was rerun; the accepted Standard + RTK baseline was reused.

| Metric | Standard + RTK | Previous Smart Compact + RTK | Promoted Smart Compact + RTK |
|---|---:|---:|---:|
| Correctness | 240/240 | 240/240 | 240/240 |
| Total tokens | 425,765 | 708,437 | 294,388 |
| Uncached input | 29,702 | 35,506 | 20,762 |
| Output tokens | 14,367 | 14,499 | 12,250 |
| Tool calls | 12 | 23 | 10 |
| Wall time | 344.427s | 368.727s | 310.427s |

The promoted policy used 30.9% fewer total tokens than Standard + RTK and 58.4% fewer than the previous Compact policy while preserving perfect functionality. These are single-run experimental results, not guaranteed savings.

See [`experiments/RESULTS.md`](experiments/RESULTS.md) for the policy iteration and [`case-study/calculator/RESULTS.md`](case-study/calculator/RESULTS.md) for the full calculator benchmark.

The original calculator benchmark used `gpt-5.6-sol` with high reasoning. Follow-ups used `gpt-5.6-luna` with high and max reasoning; all model settings and results are recorded in the calculator report.

## Three-model calculator comparison

Every model setting passed the same 960-case suite: 4 arms × 6 languages × 40 cases.

| Model / reasoning | Arm | Correctness | Total tokens | Uncached input | Output | Tool calls | Wall time |
|---|---|---:|---:|---:|---:|---:|---:|
| SOL / high | Standard + RTK | 240/240 | 425,765 | 29,702 | 14,367 | 12 | 344s |
| SOL / high | Smart Compact + RTK | 240/240 | 294,388 | 20,762 | 12,250 | 10 | 310s |
| SOL / high | Standard direct | 240/240 | 535,342 | 30,315 | 15,811 | 16 | 378s |
| SOL / high | Smart Compact direct | 240/240 | 624,298 | 30,849 | 15,145 | 20 | 426s |
| Luna / high | Standard + RTK | 240/240 | 698,797 | 64,823 | 17,782 | 16 | 386s |
| Luna / high | Smart Compact + RTK | 240/240 | 863,844 | 43,154 | 25,810 | 22 | 554s |
| Luna / high | Standard direct | 240/240 | 727,106 | 47,899 | 23,335 | 17 | 488s |
| Luna / high | Smart Compact direct | 240/240 | 992,922 | 54,529 | 18,841 | 23 | 477s |
| Luna / max | Standard + RTK | 240/240 | 936,461 | 72,561 | 32,412 | 19 | 649s |
| Luna / max | Smart Compact + RTK | 240/240 | 741,098 | 68,806 | 27,684 | 17 | 742s |
| Luna / max | Standard direct | 240/240 | 924,185 | 65,081 | 32,480 | 18 | 625s |
| Luna / max | Smart Compact direct | 240/240 | 906,240 | 63,740 | 25,860 | 21 | 505s |

Smart Compact’s total-token effect varied by model and reasoning setting:

| Model / reasoning | With RTK | Without RTK |
|---|---:|---:|
| SOL / high | -30.9% | +16.6% |
| Luna / high | +23.6% | +36.6% |
| Luna / max | -20.9% | -1.9% |

Negative values are savings. The complete input, cached-input, reasoning, source-size, and rollout data is in [`case-study/calculator/RESULTS.md`](case-study/calculator/RESULTS.md).

## RTK reference

Smart Compact was benchmarked with [RTK (Rust Token Killer)](https://github.com/rtk-ai/rtk), an independent CLI proxy that reduces noisy shell output before it reaches the model context. RTK is not bundled with this repository; it is an optional external tool used by the benchmark arms.

## Use

Attach the Smart Compact repository as the `codex-compact` skill, then invoke it explicitly:

```text
Use $codex-compact to implement this task with concise communication and economical, risk-aware tool usage.
```

The policy is adaptive rather than a hard tool budget. Destructive, security-sensitive, production, high-stakes, ambiguous, or failing work retains normal verification rigor.

Historical benchmark specifications, generated sites, and archived candidate policies retain the earlier “Codex Compact” label so their frozen inputs and artifacts remain reproducible.

## Repository layout

- [`SKILL.md`](SKILL.md): promoted skill policy.
- [`agents/openai.yaml`](agents/openai.yaml): Codex UI metadata.
- [`scripts/compact_guard.py`](scripts/compact_guard.py): risk classification and protected-literal checks.
- [`scripts/benchmark_tokens.py`](scripts/benchmark_tokens.py): token and guardrail benchmark helper.
- [`tests/`](tests): regression tests for classification and literal retention.
- [`benchmarks/`](benchmarks): text-compression benchmark cases and candidates.
- [`case-study/`](case-study): website and cross-language calculator studies.
- [`experiments/`](experiments): original and candidate policies, offline scorer, and promotion results.

## Validate

Run the regression tests:

```bash
python3 -m unittest discover -s tests -v
```

Run the calculator conformance harness:

```bash
python3 case-study/calculator/harness/run_conformance.py
```

The complete repository currently passes nine regression tests, the official Codex skill validator, and 2,880/2,880 calculator checks across the three model settings. Each model matrix separately passed 960/960.

## Benchmark limitations

- Each accepted matrix cell is a single independent agent run.
- Model decisions, caching, approvals, and tool selection introduce variance.
- Functional equivalence was scored; visual and source-code identity were not required.
- Repeat randomized trials before treating measured percentages as expected production savings.
