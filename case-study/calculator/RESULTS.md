# Cross-language calculator benchmark

Date: 2026-07-12

## Design

Four independent GPT-5.6 SOL agents each implemented six standalone expression calculators: Python, Rust, C++, Swift, JavaScript, and TypeScript. The same frozen contract was used in a 2x2 matrix:

| Arm | Smart Compact | RTK |
|---|---:|---:|
| Standard + RTK | No | Yes |
| Compact + RTK | Yes | Yes |
| Standard direct | No | No |
| Compact direct | Yes | No |

Functionality, not source or stylistic similarity, was the acceptance criterion.

## Benchmark environment

The original four-arm run used `gpt-5.6-sol` with high reasoning. The follow-up repeats the same matrix with `gpt-5.6-luna` using max reasoning; its results are recorded separately below.

## Functional result

Every first-pass implementation in the accepted four arms passed. No repairs were made.

| Language | Standard + RTK | Compact + RTK | Standard direct | Compact direct | Total |
|---|---:|---:|---:|---:|---:|
| Python | 40/40 | 40/40 | 40/40 | 40/40 | 160/160 |
| Rust | 40/40 | 40/40 | 40/40 | 40/40 | 160/160 |
| C++ | 40/40 | 40/40 | 40/40 | 40/40 | 160/160 |
| Swift | 40/40 | 40/40 | 40/40 | 40/40 | 160/160 |
| JavaScript | 40/40 | 40/40 | 40/40 | 40/40 | 160/160 |
| TypeScript | 40/40 | 40/40 | 40/40 | 40/40 | 160/160 |
| **All** | **240/240** | **240/240** | **240/240** | **240/240** | **960/960** |

The black-box suite covered arithmetic, precedence, right-associative exponentiation, unary signs, parentheses, whitespace, decimals, scientific notation, floating-point tolerance, malformed syntax, trailing tokens, zero divisors, non-finite values/results, output channels, exit status, and argument count. Rust, C++, and Swift compiled successfully in every arm.

## Raw measurements

| Arm | Wall time | Total tokens | Input | Cached input | Uncached input | Output | Reasoning output | Tool calls |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Standard + RTK | 344.427s | 425,765 | 411,398 | 381,696 | 29,702 | 14,367 | 2,220 | 12 |
| Compact + RTK | 368.727s | 708,437 | 693,938 | 658,432 | 35,506 | 14,499 | 1,756 | 23 |
| Standard direct | 377.531s | 535,342 | 519,531 | 489,216 | 30,315 | 15,811 | 2,428 | 16 |
| Compact direct | 425.963s | 624,298 | 609,153 | 578,304 | 30,849 | 15,145 | 2,257 | 20 |

## Source artifact size

| Arm | Source files | Lines | Bytes |
|---|---:|---:|---:|
| Standard + RTK | 6 | 737 | 23,716 |
| Compact + RTK | 6 | 765 | 24,540 |
| Standard direct | 6 | 759 | 24,501 |
| Compact direct | 6 | 447 | 19,415 |

Compact direct produced the smallest functionally perfect artifact: 41.1% fewer lines than Standard direct. The same artifact-size reduction did not appear in the RTK row.

## Within-row Compact effects

| Comparison | Total tokens | Uncached input | Output | Wall time | Tool calls |
|---|---:|---:|---:|---:|---:|
| Compact vs standard, with RTK | +66.4% | +19.5% | +0.9% | +7.1% | +91.7% |
| Compact vs standard, direct shell | +16.6% | +1.8% | -4.2% | +12.8% | +25.0% |

## RTK effects

| Comparison | Total tokens | Uncached input | Output | Wall time | Tool calls |
|---|---:|---:|---:|---:|---:|
| RTK vs direct, standard policy | -20.5% | -2.0% | -9.1% | -8.8% | -25.0% |
| RTK vs direct, Compact policy | +13.5% | +15.1% | -4.3% | -13.4% | +15.0% |

Negative values mean less consumption or time; positive values mean more.

## Interpretation

Correctness was perfect and indistinguishable across policies. On this task, the original Smart Compact policy did not save total tokens. It shortened outward communication and slightly reduced direct-shell output tokens, but caused more tool calls and cached context replay. The valid Compact + RTK arm was the most token-intensive cell.

RTK alone performed well under the standard policy: 20.5% fewer total tokens, 9.1% fewer output tokens, 8.8% less wall time, and 25% fewer tool calls than Standard direct. That result did not carry over cleanly when Compact was enabled because the Compact arm chose a substantially more verification-heavy workflow.

This supports a narrower conclusion than the website study: RTK can save context on implementation-heavy work, while the current Compact policy may over-trigger caution and verification on deterministic coding tasks. One sample per cell is still insufficient for a stable causal estimate.

## Adaptive policy follow-up

The trace diagnosis led to a lighter adaptive policy that batches routine work, skips unnecessary planning, runs one acceptance-focused verification, and reruns only failed or affected checks. Only this new Compact arm was executed; all prior baseline results were reused.

The adaptive arm passed 240/240 and used 294,388 total tokens, 30.9% fewer than Standard + RTK and 58.4% fewer than the previous Compact + RTK result. See the [policy iteration report](../../experiments/RESULTS.md).

## Luna max follow-up

The same four-arm matrix was rerun with `gpt-5.6-luna` and max reasoning. All four arms passed 240/240.

| Arm | Wall time | Total tokens | Input | Cached input | Uncached input | Output | Reasoning output | Tool calls |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Luna Standard + RTK | 649.303s | 936,461 | 904,049 | 831,488 | 72,561 | 32,412 | 17,453 | 19 |
| Luna Smart Compact + RTK | 742.462s | 741,098 | 713,414 | 644,608 | 68,806 | 27,684 | 12,495 | 17 |
| Luna Standard direct | 625.305s | 924,185 | 891,705 | 826,624 | 65,081 | 32,480 | 14,690 | 18 |
| Luna Smart Compact direct | 505.353s | 906,240 | 880,380 | 816,640 | 63,740 | 25,860 | 10,378 | 21 |

Within Luna, Smart Compact reduced total tokens by 20.9% with RTK and 1.9% without RTK. It reduced output tokens by 14.6% and 20.4%, respectively. The RTK Smart Compact arm used 10.5% fewer tool calls but took 14.3% longer; the direct Smart Compact arm took 19.2% less time but used 16.7% more tool calls.

Compared with the earlier `gpt-5.6-sol` high-reasoning run, Luna max used 119.9% more total tokens in the Standard + RTK arm and 151.7% more in the Smart Compact + RTK arm. Correctness remained 100% in both model settings. Max reasoning is therefore materially more expensive on this task, while Smart Compact still provides a substantial RTK-row reduction.

## Luna high follow-up

The same four-arm matrix was rerun with `gpt-5.6-luna` and high reasoning. All four arms passed 240/240.

| Arm | Wall time | Total tokens | Input | Cached input | Uncached input | Output | Reasoning output | Tool calls |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Luna high Standard + RTK | 386.136s | 698,797 | 681,015 | 616,192 | 64,823 | 17,782 | 3,827 | 16 |
| Luna high Smart Compact + RTK | 553.957s | 863,844 | 838,034 | 794,880 | 43,154 | 25,810 | 4,141 | 22 |
| Luna high Standard direct | 488.461s | 727,106 | 703,771 | 655,872 | 47,899 | 23,335 | 6,300 | 17 |
| Luna high Smart Compact direct | 476.854s | 992,922 | 974,081 | 919,552 | 54,529 | 18,841 | 5,390 | 23 |

Within Luna high, Smart Compact increased total tokens by 23.6% with RTK and 36.6% without RTK. It reduced output tokens by 45.1% and 19.3%, respectively, but used 37.5% and 35.3% more tool calls. The RTK Smart Compact arm was 43.5% slower; the direct Smart Compact arm was 2.4% faster.

Compared with Luna max, Luna high used 25.4% fewer total tokens in the Standard + RTK arm but 16.6% more in the Smart Compact + RTK arm. Compared with the original SOL/high run, Luna high used 64.1% more tokens for Standard + RTK and 193.4% more for Smart Compact + RTK. Correctness remained 100% across every model and reasoning setting.

## V6 strict-RTK model validation

The v2 Luna/high regression led to two more policy rounds and then a Codex-native profile. V6 combines an exact target-root guard, mandatory verbatim acceptance command, no hard tool-call cap, low model verbosity, a 4,000-token per-tool history limit, suppressed reasoning summaries, and a lossless operational compaction prompt.

The promoted profile was tested with an explicit RTK treatment clause on SOL at medium and high reasoning and Luna at high and max reasoning. SOL/medium received a fresh Standard + RTK control; the other three accepted Standard + RTK baselines were reused.

| Model / effort | Arm | Wall time | Total tokens | Input | Cached input | Uncached input | Output | Reasoning output | Tool calls |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| SOL / medium | Standard + RTK | 162.620s | 243,831 | 236,285 | 212,480 | 23,805 | 7,546 | 503 | 9 |
| SOL / medium | V6 profile + RTK | 110.205s | 109,223 | 104,268 | 87,808 | 16,460 | 4,955 | 200 | 4 |
| SOL / high | Standard + RTK | 344.427s | 425,765 | 411,398 | 381,696 | 29,702 | 14,367 | 2,220 | 12 |
| SOL / high | V6 profile + RTK | 161.519s | 207,227 | 200,151 | 174,080 | 26,071 | 7,076 | 477 | 7 |
| Luna / high | Standard + RTK | 386.136s | 698,797 | 681,015 | 616,192 | 64,823 | 17,782 | 3,827 | 16 |
| Luna / high | V6 profile + RTK | 225.323s | 193,312 | 181,523 | 151,552 | 29,971 | 11,789 | 2,691 | 7 |
| Luna / max | Standard + RTK | 649.303s | 936,461 | 904,049 | 831,488 | 72,561 | 32,412 | 17,453 | 19 |
| Luna / max | V6 profile + RTK | 327.849s | 188,849 | 171,558 | 142,592 | 28,966 | 17,291 | 6,999 | 6 |
| **Token-weighted aggregate** | **Standard / V6** | **1,542.486s / 824.896s** | **2,304,854 / 698,611** | **2,232,747 / 657,500** | **2,041,856 / 556,032** | **190,891 / 101,468** | **72,107 / 41,111** | **24,003 / 10,367** | **56 / 24** |

| Model / effort | Total tokens | Uncached input | Output | Reasoning output | Tool calls | Wall time |
|---|---:|---:|---:|---:|---:|---:|
| SOL / medium | -55.2% | -30.9% | -34.3% | -60.2% | -55.6% | -32.2% |
| SOL / high | -51.3% | -12.2% | -50.7% | -78.5% | -41.7% | -53.1% |
| Luna / high | -72.3% | -53.8% | -33.7% | -29.7% | -56.2% | -41.6% |
| Luna / max | -79.8% | -60.1% | -46.7% | -59.9% | -68.4% | -49.5% |
| **Aggregate** | **-69.7%** | **-46.8%** | **-43.0%** | **-56.8%** | **-57.1%** | **-46.5%** |

Every paired arm passed 240/240. The final independent report reran the four strict-v6 arms plus the new SOL/medium control and passed 1,200/1,200. The persisted rollout audit found zero RTK violations across all eight comparison traces: 93/93 submitted shell commands began with `rtk`. No strict arm wrote outside its assigned target root.

The audit invalidated the first v6 attempts, including the previously reported 294,264-token Luna/high result. Those artifacts were functionally perfect but their prompts did not restate the RTK requirement, so initial inspection and acceptance commands bypassed RTK. They were replaced with empty-root reruns and are excluded from savings claims. The promoted skill and profile now preserve an active RTK wrapper requirement explicitly, and `scripts/rtk_trace_audit.py` fails closed on direct or dynamically constructed shell commands.

Against v2, strict v6 reduced total tokens 29.6% on SOL/high, 77.6% on Luna/high, and 74.5% on Luna/max. V4 remains disqualified for scope spill and v5 for a 239/240 direct-arm correctness failure. A direct-shell v6 arm was not run because RTK is the global standard for this project.

## Spark reasoning-effort study

The local account catalog exposed `gpt-5.3-codex-spark` with low, medium, high, and xhigh reasoning. Each effort independently implemented the frozen six-language contract in a new arm. Low and medium were repeated because their first results were close; high and xhigh were not repeated after both were clearly dominated on token use and correction work.

| Effort | Run | Correctness | Total tokens | Input | Cached input | Uncached input | Output | Reasoning output |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Low | 1 | 240/240 | 399,728 | 382,957 | 352,768 | 30,189 | 16,771 | 4,065 |
| Medium | 1 | 240/240 | 379,016 | 361,839 | 286,080 | 75,759 | 17,177 | 6,193 |
| High | 1 | 240/240 | 761,470 | 741,644 | 644,352 | 97,292 | 19,826 | 7,419 |
| Xhigh | 1 | 240/240 | 851,833 | 824,289 | 747,264 | 77,025 | 27,544 | 17,378 |
| Low | 2 | 240/240 | 354,297 | 333,745 | 246,144 | 87,601 | 20,552 | 3,724 |
| Medium | 2 | 240/240 | 340,812 | 313,631 | 267,264 | 46,367 | 27,181 | 6,940 |

Low and medium both achieved 480/480 across their two runs. Medium used 719,828 aggregate total tokens versus low's 754,025, 4.5% fewer, so `spark_worker` uses medium for coding grunt work. High is reserved for retrying a concrete medium-effort failure; xhigh is excluded from grunt-work routing. These are single or paired samples and remain subject to model variance.

Raw black-box results are stored in `spark-effort-results.json` and `spark-effort-repeat-results.json`. The effort runs were ephemeral, so their final `turn.completed` usage events were captured by the benchmark orchestrator rather than preserved as rollout files.

## Spark allowance-split study

A fresh `gpt-5.6-luna` high-reasoning parent delegated the complete calculator implementation to exactly one `spark_worker` at medium effort. The parent was prohibited from writing calculator code and independently ran the conformance suite after the child reported success. No correction round was needed.

| Metric | Luna high Standard + RTK | Luna high parent | Spark child | Parent + child |
|---|---:|---:|---:|---:|
| Correctness | 240/240 | 240/240 | 240/240 | 240/240 |
| Total tokens | 698,797 | 220,671 | 766,413 | 987,084 |
| Input tokens | 681,015 | 218,128 | 744,736 | 962,864 |
| Cached input | 616,192 | 184,832 | 644,096 | 828,928 |
| Uncached input | 64,823 | 33,296 | 100,640 | 133,936 |
| Output tokens | 17,782 | 2,543 | 21,677 | 24,220 |
| Reasoning output | 3,827 | 1,136 | 10,967 | 12,103 |
| Tool calls | 16 | 9 | 18 | 27 |
| Wall time | 386.136s | 122.631s | 59.814s nested | 122.631s |

Relative to the reused Luna high Standard + RTK baseline, the parent consumed 68.4% fewer total tokens, 48.6% fewer uncached input tokens, 85.7% fewer output tokens, and 43.8% fewer tool calls. This is the study's primary success criterion because eligible Pro accounts meter Spark through a separate usage limit: the implementation work moved off the main-model bucket while correctness remained perfect.

Combined parent-plus-child usage was 41.3% higher. That number crosses two different allowance buckets, so it is secondary capacity telemetry rather than the optimization target or a regression. It remains useful for avoiding wasteful delegation of tiny tasks and for understanding total system load.

The result verifies token-accounting separation at the rollout level. It does not prove the provider's internal subscription accounting formula; plan limits may use different weights or change over time.

## Treatment audit

The first attempted Compact + RTK agent used direct shell commands despite its assignment. Its artifact and rollout were excluded, preserved under `compact-rtk-noncompliant`, and replaced with a fresh run. Trace inspection confirmed that every shell command in the replacement used RTK, including batched commands. The standard RTK arm also used RTK throughout; both direct arms used zero RTK commands.

## Rollouts

- Standard + RTK: `019f5672-5733-7032-9b23-3b891aa5b4a1`
- Compact + RTK: `019f567b-2b73-7b62-9703-9dcb341dad6b`
- Standard direct: `019f5672-5b01-7b51-ab4c-88b09dbcf148`
- Compact direct: `019f5672-5f89-7430-8764-69a9872c2a3d`
- Excluded noncompliant Compact + RTK: `019f5672-528d-75c0-b338-32bf1cc3dbf0`

Luna max follow-up rollouts:

- Luna Standard + RTK: `019f56e6-6c7f-7230-931a-d1d5b5359161`
- Luna Smart Compact + RTK: `019f56e6-63fa-7901-bb83-e26bf2c8dc01`
- Luna Standard direct: `019f56e6-687e-7f82-9d5b-8e4f1aaed1f7`
- Luna Smart Compact direct: `019f56e6-705a-77f0-8511-e0f192e76a70`

Luna high-reasoning follow-up rollouts:

- Luna high Standard + RTK: `019f56f8-ff20-7133-8bf1-1ec61963f6e7`
- Luna high Smart Compact + RTK: `019f56f9-034f-7da0-9b79-23f121ea1d33`
- Luna high Standard direct: `019f56f9-07da-7412-9a57-7230d48d2e62`
- Luna high Smart Compact direct: `019f56f9-0bca-7fc3-a198-731a35a3f470`

Spark allowance-split rollouts:

- Luna high parent: `019f57c4-5014-7073-a0f0-7a447479fdd4`
- Spark medium child: `019f57c4-e052-7ee2-92d5-f5e8a5a244da`

V6 strict-RTK validation rollouts:

- SOL medium Standard + RTK: `019f57e7-e69d-73a1-af16-38aa9cb13255`
- SOL medium v6 profile + RTK: `019f57f1-42d9-7570-aa26-99b1c2b4dc4b`
- SOL high v6 profile + RTK: `019f57f1-6a38-74f1-9455-3eb5380ada8f`
- Luna high v6 profile + RTK: `019f57f8-40f3-79c1-876d-0124fa1f4243`
- Luna max v6 profile + RTK: `019f57f1-464f-7b22-95dd-69a3a3dc7bca`

Excluded partial-RTK v6 rollouts:

- Luna high: `019f57d3-f20e-7223-895c-f65171a68a54`
- Luna max: `019f57e7-ee48-7ee0-8652-ce9d135dfe92`
- SOL high: `019f57e7-ea86-78c2-9dd1-dfb92d1a6799`
- SOL medium: `019f57e7-f264-7d81-b688-f64a447d8f1b`

Machine-readable reports: `v6-model-matrix-results.json` and `v6-model-validation-results.json`.
