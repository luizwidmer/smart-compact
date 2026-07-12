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
