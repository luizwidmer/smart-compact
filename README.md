# Smart Compact

[Smart Compact](https://github.com/luizwidmer/smart-compact) is an experimental Codex optimization package for reducing main-model communication and context usage without weakening correctness or safety. It combines an acceptance-gated skill, an optional native Codex profile, RTK compatibility, and capability-gated Spark offload.

## Status

Smart Compact is defined by [`SKILL.md`](SKILL.md) and [`profiles/smart-compact.config.toml`](profiles/smart-compact.config.toml). The skill works by itself; the optional profile adds native low verbosity, bounded per-tool history, suppressed reasoning summaries, and lossless machine-oriented compaction. Its skill identifier is `smart-compact`, invoked as `$smart-compact`.

## Install

Install the complete package with one command:

```bash
curl -fsSL https://raw.githubusercontent.com/luizwidmer/smart-compact/main/install.sh | sh
```

Or install from a checkout:

```bash
git clone https://github.com/luizwidmer/smart-compact.git
cd smart-compact
./install.sh
```

The installer is idempotent and does not overwrite differing files unless you pass `--force`.

| Component | Default target | Behavior |
|---|---|---|
| Smart Compact skill | `$HOME/.agents/skills/smart-compact` | Always installed |
| Native profile | `${CODEX_HOME:-$HOME/.codex}/smart-compact.config.toml` | Installed by default; activate with `codex --profile smart-compact` |
| Spark worker | `${CODEX_HOME:-$HOME/.codex}/agents/spark-worker.toml` | Installed only when the local model catalog exposes Spark |
| RTK | Existing executable on `PATH` | Detected and reported; never installed or modified |

Common options:

```bash
./install.sh --dry-run               # preview without writing
./install.sh --force                 # update differing managed files
./install.sh --no-spark              # skip Spark detection and installation
./install.sh --no-profile            # install the skill without the profile
```

When using the remote one-liner, pass options through `sh -s --`, for example:

```bash
curl -fsSL https://raw.githubusercontent.com/luizwidmer/smart-compact/main/install.sh | sh -s -- --dry-run
```

Start a new Codex task after installation so skill and custom-agent discovery refreshes, then invoke `$smart-compact`. Codex documents global skills under `$HOME/.agents/skills`, profile files under `$CODEX_HOME/<name>.config.toml`, and personal custom agents under `~/.codex/agents`; see [Skills](https://learn.chatgpt.com/docs/customization/overview#skills), [configuration precedence](https://learn.chatgpt.com/docs/config-file/config-basic#configuration-precedence), and [custom agents](https://learn.chatgpt.com/docs/agent-configuration/subagents#custom-agents).

## Measured result

V6 was validated under strict RTK enforcement on four model/effort settings. The original accepted SOL/high, Luna/high, and Luna/max Standard + RTK baselines were reused; SOL/medium received a fresh Standard + RTK control.

| Model / effort | Standard + RTK | Smart Compact v6 + RTK | Total savings | Tool calls | Wall time | Correctness |
|---|---:|---:|---:|---:|---:|---:|
| SOL / medium | 243,831 | 109,223 | 55.2% | 9 → 4 | 162.620s → 110.205s | 240/240 both |
| SOL / high | 425,765 | 207,227 | 51.3% | 12 → 7 | 344.427s → 161.519s | 240/240 both |
| Luna / high | 698,797 | 193,312 | 72.3% | 16 → 7 | 386.136s → 225.323s | 240/240 both |
| Luna / max | 936,461 | 188,849 | 79.8% | 19 → 6 | 649.303s → 327.849s | 240/240 both |
| **Token-weighted aggregate** | **2,304,854** | **698,611** | **69.7%** | **56 → 24** | **1,542.486s → 824.896s** | **960/960 both** |

The savings were positive in every tested setting:

| Model / effort | Uncached input | Output | Reasoning output | Tool calls | Wall time |
|---|---:|---:|---:|---:|---:|
| SOL / medium | 30.9% | 34.3% | 60.2% | 55.6% | 32.2% |
| SOL / high | 12.2% | 50.7% | 78.5% | 41.7% | 53.1% |
| Luna / high | 53.8% | 33.7% | 29.7% | 56.2% | 41.6% |
| Luna / max | 60.1% | 46.7% | 59.9% | 68.4% | 49.5% |
| **Aggregate** | **46.8%** | **43.0%** | **56.8%** | **57.1%** | **46.5%** |

The accepted model matrix passed 960/960 functional checks in both control and Smart Compact arms. Generated benchmark projects, candidate policies, traces, and language fixtures are intentionally omitted from the package; this README retains only the accepted aggregate results. These are single-run experimental measurements, not guaranteed production savings.

## Native Codex profile

The optional profile uses supported Codex controls instead of grammar stripping:

- `model_verbosity = "low"` reduces visible prose without a large style prompt.
- `tool_output_token_limit = 4000` bounds each stored tool result before later turns replay it.
- `model_reasoning_summary = "none"` removes surfaced reasoning summaries; it does not alter hidden reasoning effort.
- `compact_prompt` preserves exact operational state in a terse machine-oriented handoff while dropping narration and duplicate evidence.
- `agents.interrupt_message = false` avoids an unnecessary model-visible interruption message.

The package installer installs this profile by default. To install only the profile from a checkout:

```bash
python3 scripts/install_codex_profile.py
codex --profile smart-compact
```

The installer refuses to overwrite a different existing profile unless `--force` is supplied. The profile is optional because global output and tool-history preferences are user choices; the skill remains portable across Codex surfaces. See the official [Codex configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference#configtoml).

## Why Smart Compact does not compress hidden thought

Current Caveman is fundamentally an output-style prompt plus persistence hooks; its own honest accounting says it does not compress input, context, or model thinking and adds about 1–1.5k input tokens per turn. Smart Compact adopts its useful lesson—structured, narrow handoffs—but not article deletion or repeated style injection. [Caveman's honest numbers](https://github.com/JuliusBrussee/caveman/blob/main/docs/HONEST-NUMBERS.md)

A recent eight-model study likewise found output constraints can reduce realized cost, while grammar-stripped input increased cost and reduced accuracy. Smart Compact therefore keeps specifications and technical literals intact. [CAVEWOMAN paper](https://arxiv.org/abs/2606.24083)

Codex does not provide a supported way for this project to rewrite private chain-of-thought into a “100% machine thought” language. The profile can select reasoning effort, suppress reasoning summaries, and improve conversation compaction; hidden reasoning remains model-controlled.

## Optional Spark offload

Smart Compact includes a custom `spark_worker` agent pinned to `gpt-5.3-codex-spark`. It is intended for bounded, text-only, mechanical work with a clear acceptance check. The parent model keeps architecture, risky decisions, integration, and final verification. If Spark is absent or cannot start, Smart Compact continues with the normal worker or locally.

The reasoning-effort study ran the same six-language calculator task at every Spark-supported effort. All arms eventually passed, but medium was the best measured coding default. Across two low-versus-medium runs, both settings scored 480/480; medium used 719,828 total tokens versus low's 754,025, a 4.5% reduction. High and xhigh used roughly twice the first-round tokens and required more correction work.

The actual allowance-split case study used a Luna/high parent and one Spark/medium worker:

| Arm | Correctness | Main-model tokens | Spark tokens | Combined tokens | Parent wall time |
|---|---:|---:|---:|---:|---:|
| Luna/high Standard + RTK | 240/240 | 698,797 | 0 | 698,797 | 386.136s |
| Luna/high parent + Spark/medium worker | 240/240 | 220,671 | 766,413 | 987,084 | 122.631s |

Offload reduced main-model token use by 68.4% and parent wall time by 68.2%. That is the primary result: eligible Pro accounts give Spark a separate usage limit, so moving bounded work from Luna to Spark protects the main-model allowance. Combined model tokens rose 41.3%, but that crosses two different allowance buckets and is recorded only as secondary capacity telemetry, not as a failure of the offload strategy. The result is a single controlled run and does not establish the provider's internal metering formula.

The package installer performs this capability check automatically. To inspect or install only the optional global role from a checkout:

```bash
python3 scripts/install_spark_agent.py --check
python3 scripts/install_spark_agent.py
```

If Spark is not in the account's local model catalog, the installer exits successfully without changing anything. Start a new Codex task after installation so the subagent tool schema can discover `spark_worker`. See the official [Codex subagent model guidance](https://learn.chatgpt.com/docs/agent-configuration/subagents#choosing-models-and-reasoning) and [plan usage notes](https://learn.chatgpt.com/docs/pricing#what-are-the-usage-limits-for-my-plan).

## RTK reference

Smart Compact was benchmarked with [RTK (Rust Token Killer)](https://github.com/rtk-ai/rtk), an independent CLI proxy that reduces noisy shell output before it reaches the model context. RTK is not bundled with this repository; it is optional for users but mandatory in every arm labeled `+ RTK`, and those persisted traces are now audited before acceptance.

## Use

After installation, start a new task and invoke the skill explicitly:

```text
Use $smart-compact to implement this task with concise communication and economical, risk-aware tool usage.
```

The policy is adaptive rather than a hard tool budget. Destructive, security-sensitive, production, high-stakes, ambiguous, or failing work retains normal verification rigor.

## Repository layout

- [`install.sh`](install.sh): local and remote one-command bootstrap.
- [`SKILL.md`](SKILL.md): promoted skill policy.
- [`agents/openai.yaml`](agents/openai.yaml): Codex UI metadata.
- [`profiles/smart-compact.config.toml`](profiles/smart-compact.config.toml): optional native Codex profile.
- [`requirements-benchmark.txt`](requirements-benchmark.txt): optional dependency for exact token scoring.
- [`benchmarks/cases.json`](benchmarks/cases.json): source cases for compression and safety scoring.
- [`case-study/SPEC.md`](case-study/SPEC.md): reproducible website benchmark contract.
- [`case-study/calculator/SPEC.md`](case-study/calculator/SPEC.md): reproducible six-language calculator contract.
- [`case-study/harness/`](case-study/harness): rollout analysis and website contract tools.
- [`case-study/calculator/harness/`](case-study/calculator/harness): cross-language conformance runner.
- [`scripts/benchmark_tokens.py`](scripts/benchmark_tokens.py): token and guardrail benchmark runner.
- [`scripts/compact_guard.py`](scripts/compact_guard.py): risk classification and literal-retention checks.
- [`scripts/install_codex_profile.py`](scripts/install_codex_profile.py): non-overwriting profile installer.
- [`scripts/install_smart_compact.py`](scripts/install_smart_compact.py): unified idempotent package installer.
- [`scripts/install_spark_agent.py`](scripts/install_spark_agent.py): capability-gated Spark role installer.
- [`scripts/rtk_trace_audit.py`](scripts/rtk_trace_audit.py): fail-closed RTK rollout auditor.
- [`scripts/score_policies.py`](scripts/score_policies.py): reusable policy-size and safety scorer.
- [`tests/`](tests): package and benchmark-tool regression tests.

## Benchmark toolkit

Generated projects and result snapshots are not committed. Recreate new arms from the retained contracts, then run the relevant tools:

```bash
python3 -m pip install -r requirements-benchmark.txt

python3 scripts/benchmark_tokens.py \
  --cases benchmarks/cases.json \
  --candidates /path/to/candidates.json

python3 scripts/score_policies.py SKILL.md /path/to/candidate/SKILL.md

python3 case-study/harness/analyze_rollout.py \
  --baseline /path/to/baseline.jsonl \
  --smart-compact /path/to/smart-compact.jsonl

python3 scripts/rtk_trace_audit.py /path/to/rollout.jsonl
python3 case-study/harness/check_contract.py /path/to/generated-site

python3 case-study/calculator/harness/run_conformance.py \
  --root /path/to/generated-calculator-arms \
  --arms standard-rtk smart-compact-rtk
```

## Validate

Run the regression tests:

```bash
python3 -m unittest discover -s tests -v
```

The lean package currently passes twenty-nine regression tests and the official Codex skill validator. Historical benchmark correctness and token results are summarized above without shipping generated benchmark artifacts.

## Benchmark limitations

- Each accepted matrix cell is a single independent agent run.
- Model decisions, caching, approvals, and tool selection introduce variance.
- Functional equivalence was scored; visual and source-code identity were not required.
- Repeat randomized trials before treating measured percentages as expected production savings.

## License

Copyright 2026 Luiz Widmer. Smart Compact is licensed under the [Apache License 2.0](LICENSE); see [NOTICE](NOTICE) for attribution.
