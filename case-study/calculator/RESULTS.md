# Cross-language calculator benchmark

Date: 2026-07-12

## Design

Four independent GPT-5.6 SOL agents each implemented six standalone expression calculators: Python, Rust, C++, Swift, JavaScript, and TypeScript. The same frozen contract was used in a 2x2 matrix:

| Arm | Codex Compact | RTK |
|---|---:|---:|
| Standard + RTK | No | Yes |
| Compact + RTK | Yes | Yes |
| Standard direct | No | No |
| Compact direct | Yes | No |

Functionality, not source or stylistic similarity, was the acceptance criterion.

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

Correctness was perfect and indistinguishable across policies. On this task, Codex Compact did not save total tokens. It shortened outward communication and slightly reduced direct-shell output tokens, but caused more tool calls and cached context replay. The valid Compact + RTK arm was the most token-intensive cell.

RTK alone performed well under the standard policy: 20.5% fewer total tokens, 9.1% fewer output tokens, 8.8% less wall time, and 25% fewer tool calls than Standard direct. That result did not carry over cleanly when Compact was enabled because the Compact arm chose a substantially more verification-heavy workflow.

This supports a narrower conclusion than the website study: RTK can save context on implementation-heavy work, while the current Compact policy may over-trigger caution and verification on deterministic coding tasks. One sample per cell is still insufficient for a stable causal estimate.

## Adaptive policy follow-up

The trace diagnosis led to a lighter adaptive policy that batches routine work, skips unnecessary planning, runs one acceptance-focused verification, and reruns only failed or affected checks. Only this new Compact arm was executed; all prior baseline results were reused.

The adaptive arm passed 240/240 and used 294,388 total tokens, 30.9% fewer than Standard + RTK and 58.4% fewer than the previous Compact + RTK result. See the [policy iteration report](../../experiments/RESULTS.md).

## Treatment audit

The first attempted Compact + RTK agent used direct shell commands despite its assignment. Its artifact and rollout were excluded, preserved under `compact-rtk-noncompliant`, and replaced with a fresh run. Trace inspection confirmed that every shell command in the replacement used RTK, including batched commands. The standard RTK arm also used RTK throughout; both direct arms used zero RTK commands.

## Rollouts

- Standard + RTK: `019f5672-5733-7032-9b23-3b891aa5b4a1`
- Compact + RTK: `019f567b-2b73-7b62-9703-9dcb341dad6b`
- Standard direct: `019f5672-5b01-7b51-ab4c-88b09dbcf148`
- Compact direct: `019f5672-5f89-7430-8764-69a9872c2a3d`
- Excluded noncompliant Compact + RTK: `019f5672-528d-75c0-b338-32bf1cc3dbf0`
