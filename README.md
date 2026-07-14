# Smart Compact

[Smart Compact](https://github.com/luizwidmer/smart-compact) is an experimental Codex optimization package for reducing main-model communication and context usage without weakening correctness or safety. It combines an acceptance-gated skill, native Codex profile controls, an in-app profile-picker plugin, RTK compatibility, and capability-gated Spark offload.

## Status

Smart Compact is defined by [`SKILL.md`](SKILL.md), [`profiles/smart-compact.config.toml`](profiles/smart-compact.config.toml), and [`plugin/`](plugin). The skill works by itself; the optional profile adds native low verbosity, bounded per-tool history, suppressed reasoning summaries, lossless machine-oriented compaction, and the Spark delegation preflight. The plugin bundles that skill and adds supported app profile selection. Its skill identifier is `smart-compact`, invoked as `$smart-compact`.

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
| Codex plugin | `$HOME/plugins/smart-compact` | Adds `@Smart Compact`, an in-app profile picker, and the bundled skill |
| Spark worker | `${CODEX_HOME:-$HOME/.codex}/agents/spark-worker.toml` | Installed only when the local model catalog exposes Spark |
| RTK | Existing executable on `PATH` | Detected and reported; never installed or modified |

Common options:

```bash
./install.sh --dry-run               # preview without writing
./install.sh --force                 # update differing managed files
./install.sh --no-spark              # skip Spark detection and installation
./install.sh --no-profile            # install the skill without the profile
./install.sh --no-plugin             # skip plugin installation and activation
./install.sh --make-default          # promote Smart Compact into shared config.toml
```

When using the remote one-liner, pass options through `sh -s --`, for example:

```bash
curl -fsSL https://raw.githubusercontent.com/luizwidmer/smart-compact/main/install.sh | sh -s -- --dry-run
```

Restart Codex or start a new task after installation so plugin, skill, and custom-agent discovery refreshes. Use `@Smart Compact` for the app profile picker or `$smart-compact` to apply the efficiency policy in the current task. Codex documents global skills under `$HOME/.agents/skills`, profile files under `$CODEX_HOME/<name>.config.toml`, and personal custom agents under `~/.codex/agents`; see [Skills](https://learn.chatgpt.com/docs/customization/overview#skills), [configuration precedence](https://learn.chatgpt.com/docs/config-file/config-basic#configuration-precedence), and [custom agents](https://learn.chatgpt.com/docs/agent-configuration/subagents#custom-agents).

## Measured results

### Agentic Spark/no-Spark matrix (2026-07-14)

The new hermetic agentic suite ran four realistic local task shapes in both Spark-available and isolated no-Spark arms, with three randomized paired trials per case. The parent was `gpt-5.6-luna` at high effort, the worker was `gpt-5.3-codex-spark`, and three case/trial pairs ran concurrently. All 24 runs passed their hidden checks; all 12 pairs passed routing, worker-completion, scope, acceptance-command, usage-accounting, and RTK audits.

Positive token changes below mean the Spark-available arm used more tokens. Percentages are medians of the three within-case paired changes, not ratios of the pooled arm medians.

| Case | Spark routing | Quality parity | Parent-token change | Combined-token change |
|---|---:|---:|---:|---:|
| `release-readiness` | 0/3 children, expected | 3/3 | +21.7% | +21.7% |
| `incident-triage` | 3/3 exact worker, completed | 3/3 | +28.0% | +47.4% |
| `order-reconciliation` | 3/3 exact worker, completed | 3/3 | +69.0% | +92.1% |
| `ttl-boundary-regression` | 0/3 children, expected | 3/3 | +0.1% | +0.1% |
| **All 12 pairs** | **12/12 routing-valid** | **12/12** | **+28.2%** | **+37.3%** |

Across arms, the Spark-available median was 168,805 parent and 182,899 combined tokens; no-Spark was 123,686 parent/combined tokens. The six actually offloaded pairs had a +31.35% median parent-token change and +50.2% combined-token change. The matrix therefore validates quality-preserving routing and fallback behavior, but it does **not** support Spark as a general token or latency optimization. Three-way parallel execution makes the observed +22.5% median wall-time change contention-affected diagnostic data, not a clean speed estimate.

This negative result tightened the default gate: six targets alone no longer justify automatic offload. Smart Compact now requires either an explicit user objective to protect the parent-model allowance despite possible total-cost overhead, or repeated paired evidence that a substantially similar workload saves parent tokens. The experimental fixtures still force both arms so the tradeoff remains measurable. Full protocol, per-arm medians, hashes, and limitations are in [`RESEARCH.md`](RESEARCH.md).

### Historical V6 compression matrix

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

## Codex profile and app picker

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

Codex exposes named config profiles directly through the CLI. Smart Compact adds the supported app workflow as a personal plugin: select `@Smart Compact` in the composer and ask it to start a profiled task. Its MCP tool uses Codex's `openai/form` extension to show an in-app picker containing:

- Smart Compact, recommended and backed by the installed profile or the plugin's equivalent bundled configuration.
- Every safe profile discovered at `${CODEX_HOME:-$HOME/.codex}/*.config.toml`.
- Codex default, which uses only the shared configuration layers.

The plugin creates one empty task with the selected profile and returns its official `codex://threads/<id>` link. It does not modify the current task, replay the current prompt, auto-run work, patch the Codex app, or launch a GUI process from the MCP server. Task creation uses the published per-thread app-server configuration and deep-link interfaces; `codex app-server` is currently marked experimental. The stable fallback remains `codex --profile smart-compact` followed by `/app`.

### What counts as a task

In Codex, a **task** is the persistent conversation or thread represented by one item in **Recent Tasks**. It is not the physical app window and it is not the current prompt. Each prompt and the resulting agent work form a new **turn** inside the same task.

- Sending another prompt in the current conversation continues the same task.
- Reopening an item from **Recent Tasks** resumes that same task and transcript.
- Starting **New Task**, using `/new`, or forking creates a separate task; a fork begins with inherited context but has its own identity afterward.
- Opening another Codex window does not by itself create a task; the task is determined by which conversation or thread that window displays.

This boundary matters for profiles: Codex selects the profile when a task is created. The Smart Compact picker therefore creates a new empty task with the selected profile. Sending a new prompt in the current task cannot switch that task's profile. After following the returned task link, send the intended prompt in the newly created task.

To make Smart Compact the default for both CLI and desktop tasks without patching the app, promote its managed settings into the shared base config:

```bash
./install.sh --make-default
```

This is an explicit opt-in. It preserves unrelated model, reasoning-effort, project, plugin, MCP, hook, desktop, and other settings; it changes only Smart Compact's five top-level keys and `agents.interrupt_message`. Before updating an existing `${CODEX_HOME:-$HOME/.codex}/config.toml`, it creates a timestamped, hash-verified backup under `${CODEX_HOME:-$HOME/.codex}/backups/smart-compact/` and preserves the original file mode. `--dry-run --make-default` previews the operation without writing or creating a backup.

The installer refuses to overwrite a different existing managed package file unless `--force` is supplied. The profile remains optional because global output and tool-history preferences are user choices; the skill remains portable across Codex surfaces. See the official [profile documentation](https://learn.chatgpt.com/docs/config-file/config-advanced#profiles), [configuration precedence](https://learn.chatgpt.com/docs/config-file/config-basic#configuration-precedence), [desktop task deep links](https://learn.chatgpt.com/docs/reference/commands#tasks), and [Codex app-server](https://learn.chatgpt.com/docs/app-server).

## Why Smart Compact does not compress hidden thought

Current Caveman is fundamentally an output-style prompt plus persistence hooks; its own honest accounting says it does not compress input, context, or model thinking and adds about 1–1.5k input tokens per turn. Smart Compact adopts its useful lesson—structured, narrow handoffs—but not article deletion or repeated style injection. [Caveman's honest numbers](https://github.com/JuliusBrussee/caveman/blob/main/docs/HONEST-NUMBERS.md)

A recent eight-model study likewise found output constraints can reduce realized cost, while grammar-stripped input increased cost and reduced accuracy. Smart Compact therefore keeps specifications and technical literals intact. [CAVEWOMAN paper](https://arxiv.org/abs/2606.24083)

Codex does not provide a supported way for this project to rewrite private chain-of-thought into a “100% machine thought” language. The profile can select reasoning effort, suppress reasoning summaries, and improve conversation compaction; hidden reasoning remains model-controlled.

## Optional Spark offload

Smart Compact includes a custom `spark_worker` agent pinned to `gpt-5.3-codex-spark`. It is intended for bounded, text-only, mechanical work with a clear acceptance check. The parent model keeps architecture, risky decisions, integration, and final verification. If Spark is absent or cannot start, Smart Compact continues locally; it does not substitute another agent for `spark_worker`.

The original policy used the qualitative gate “large enough to justify a handoff.” A later six-target gate made selection deterministic, but the repeated agentic matrix showed that target count alone did not predict an efficiency win. The current gate runs a preflight for nontrivial tasks, then permits one Spark worker only when a parallel eligible sidecar contains homogeneous work across at least six exclusive targets **and** either the user explicitly prioritizes preserving the parent-model allowance despite possible combined-token or latency overhead, or repeated paired measurements on a substantially similar workload demonstrate parent-token savings. General requests for speed or token efficiency stay local without that evidence. The selected child must be `spark_worker`, not a built-in or dynamically named substitute. It receives exclusive targets, while the parent keeps disjoint work, integration, and final verification. For cross-source semantic aggregates, the parent runs a deterministic source-to-artifact assertion before acceptance rather than trusting visual or child totals. Tiny, sequential, critical-path, overlapping, risky, and unverifiable work stays local. One Spark worker is active by default when the full gate is met. The retained [`benchmarks/spark-cases.json`](benchmarks/spark-cases.json) fixture makes the evidence/intent gate regression-testable.

The post-gate autonomous app-server smoke explicitly prioritized the parent allowance, supplied one qualifying six-file read-only sidecar, selected `/root/spark_worker` exactly once, completed the parent turn, and made no edits. This validates the intentional-offload branch of the policy, not token efficiency or a general spawn recommendation.

The reasoning-effort study ran the same six-language calculator task at every Spark-supported effort. All arms eventually passed, but medium was the best measured coding default. Across two low-versus-medium runs, both settings scored 480/480; medium used 719,828 total tokens versus low's 754,025, a 4.5% reduction. High and xhigh used roughly twice the first-round tokens and required more correction work.

The historical single-run allowance-split case study used a Luna/high parent and one Spark/medium worker:

| Arm | Correctness | Main-model tokens | Spark tokens | Combined tokens | Parent wall time |
|---|---:|---:|---:|---:|---:|
| Luna/high Standard + RTK | 240/240 | 698,797 | 0 | 698,797 | 386.136s |
| Luna/high parent + Spark/medium worker | 240/240 | 220,671 | 766,413 | 987,084 | 122.631s |

That historical run reduced main-model token use by 68.4% and parent wall time by 68.2%, while combined model tokens rose 41.3%. The repeated 2026-07-14 matrix did not reproduce the parent-token saving: its actually offloaded pairs used 31.35% more parent tokens at the paired median. The older case remains evidence that allowance shifting can work for a particular workload, not evidence that generic bounded work protects the parent allowance. Provider-internal metering and separate usage buckets are not inferred from these token traces.

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
- [`plugin/`](plugin): personal Codex plugin with the bundled skill and `openai/form` profile picker.
- [`requirements-benchmark.txt`](requirements-benchmark.txt): optional dependency for exact token scoring.
- [`RESEARCH.md`](RESEARCH.md): benchmark source review, paired protocol, metrics, and limitations.
- [`benchmarks/agentic-cases.json`](benchmarks/agentic-cases.json): frozen realistic fixtures, oracle overlays, and hidden checks.
- [`benchmarks/cases.json`](benchmarks/cases.json): source cases for compression and safety scoring.
- [`benchmarks/spark-cases.json`](benchmarks/spark-cases.json): structured Spark delegation decision cases.
- [`case-study/SPEC.md`](case-study/SPEC.md): reproducible website benchmark contract.
- [`case-study/calculator/SPEC.md`](case-study/calculator/SPEC.md): reproducible six-language calculator contract.
- [`case-study/harness/`](case-study/harness): rollout analysis and website contract tools.
- [`case-study/calculator/harness/`](case-study/calculator/harness): cross-language conformance runner.
- [`scripts/benchmark_tokens.py`](scripts/benchmark_tokens.py): token and guardrail benchmark runner.
- [`scripts/benchmark_agentic.py`](scripts/benchmark_agentic.py): paired hermetic Spark/no-Spark workload runner.
- [`scripts/benchmark_spark_spawn.py`](scripts/benchmark_spark_spawn.py): ephemeral autonomous Spark-spawn check.
- [`scripts/compact_guard.py`](scripts/compact_guard.py): risk classification and literal-retention checks.
- [`scripts/default_profile.py`](scripts/default_profile.py): comment-preserving shared-config promotion and backup logic.
- [`scripts/install_codex_profile.py`](scripts/install_codex_profile.py): non-overwriting profile installer.
- [`scripts/install_smart_compact.py`](scripts/install_smart_compact.py): unified idempotent package installer.
- [`scripts/install_spark_agent.py`](scripts/install_spark_agent.py): capability-gated Spark role installer.
- [`scripts/open_app_task.py`](scripts/open_app_task.py): app-server client retained for benchmark and protocol diagnostics.
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

python3 scripts/benchmark_agentic.py \
  --repetitions 3 \
  --jobs 3 \
  --profile profiles/smart-compact.config.toml \
  --model gpt-5.6-luna \
  --effort high \
  --output /path/to/generated-results.json

python3 scripts/score_policies.py SKILL.md /path/to/candidate/SKILL.md

python3 scripts/benchmark_spark_spawn.py /path/to/repository

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

The lean package passes its current 70-test regression suite and the official Codex plugin validator. Historical benchmark correctness and token results are summarized above without shipping generated benchmark artifacts.

## Benchmark limitations

- Historical V6 compression cells are single independent agent runs; the 2026-07-14 agentic matrix uses three trials per case and arm.
- Model decisions, caching, approvals, and tool selection introduce variance.
- Functional equivalence was scored; visual and source-code identity were not required.
- Agentic `--jobs 3` execution was intentionally parallel, so its wall-time values are contention-affected diagnostics rather than clean latency estimates.
- The local synthetic suite is small, and `order-reconciliation` participated in tuning; its original held-out label does not support an untouched-held-out claim.
- `publishable=true` means the harness completeness and integrity predicates passed, not that the result is statistically or externally validated.
- Repeat randomized trials on substantially similar workloads before treating measured percentages as expected production savings.

## License

Copyright 2026 Luiz Widmer. Smart Compact is licensed under the [Apache License 2.0](LICENSE); see [NOTICE](NOTICE) for attribution.
