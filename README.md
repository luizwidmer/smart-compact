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

The complete repository currently passes nine regression tests, the official Codex skill validator, and 960/960 accepted calculator checks. The promoted v2 arm separately passes 240/240 checks.

## Benchmark limitations

- Each accepted matrix cell is a single independent agent run.
- Model decisions, caching, approvals, and tool selection introduce variance.
- Functional equivalence was scored; visual and source-code identity were not required.
- Repeat randomized trials before treating measured percentages as expected production savings.
