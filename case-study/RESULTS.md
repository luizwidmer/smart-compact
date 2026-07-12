# Relay Bench 2x2 case study

Date: 2026-07-12

## Design

Four independent GPT-5.6 SOL agents received the same frozen product contract, Sites starter, model family, and reasoning level. The factors were:

| Arm | Smart Compact | RTK |
|---|---:|---:|
| Standard + RTK | No | Yes |
| Compact + RTK | Yes | Yes |
| Standard direct | No | No |
| Compact direct | Yes | No |

Visual styling was allowed to vary. Validity was based on the frozen functional contract rather than pixel identity.

## Functional validation

All four arms passed 12/12 checks:

1. Exact browser title and description.
2. Required semantic landmarks and test-hook order.
3. Exactly one heading and required product copy.
4. Correct initial 7-run metrics.
5. Correct initial `aria-pressed` state.
6. Correct 30-run metric transition.
7. Correct return to the 7-run state.
8. Methodology content hidden initially.
9. Methodology reveal, exact copy, label, and `aria-expanded` state.
10. Methodology hide reversal.
11. Comparison navigation target and scrolling.
12. Native buttons, reduced-motion rule, one-column mobile layout, no 390px overflow, and no console errors.

All four production builds passed.

## Raw measurements

| Arm | Wall time | Total tokens | Input | Cached input | Uncached input | Output | Reasoning output | Tool calls |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Standard + RTK | 199.308s | 461,099 | 453,153 | 428,288 | 24,865 | 7,946 | 887 | 14 |
| Compact + RTK | 223.702s | 323,254 | 313,275 | 288,256 | 25,019 | 9,979 | 1,310 | 9 |
| Standard direct | 228.793s | 449,330 | 439,768 | 407,552 | 32,216 | 9,562 | 1,460 | 11 |
| Compact direct | 239.759s | 446,456 | 437,094 | 377,856 | 59,238 | 9,362 | 1,964 | 11 |

## Within-row effects

| Comparison | Total-token change | Uncached-input change | Output change | Wall-time change | Tool-call change |
|---|---:|---:|---:|---:|---:|
| Compact vs standard, with RTK | -29.9% | +0.6% | +25.6% | +12.2% | -35.7% |
| Compact vs standard, direct shell | -0.6% | +83.9% | -2.1% | +4.8% | 0.0% |

## RTK effects within each policy

| Comparison | Total-token change | Uncached-input change | Output change | Wall-time change | Tool-call change |
|---|---:|---:|---:|---:|---:|
| RTK vs direct, standard policy | +2.6% | -22.8% | -16.9% | -12.9% | +27.3% |
| RTK vs direct, Compact policy | -27.6% | -57.8% | +6.6% | -6.7% | -18.2% |

Negative values mean less consumption or time; positive values mean more.

## Interpretation

This single-run case study demonstrates functional parity, but it does not establish stable causal savings. The strongest observed result was the Compact + RTK arm: 29.9% fewer total tokens than Standard + RTK and 27.6% fewer than Compact direct. Compact alone was nearly neutral on total tokens in the direct-shell row and used substantially more uncached input. RTK alone reduced uncached input, output, and wall time, but used 2.6% more total tokens because cached input and tool-call count were higher.

The interaction is plausible: RTK compresses command output while Compact encourages fewer context-heavy operations. However, independent implementations, cache behavior, tool-call choices, and one sample per cell remain confounders. Repeat the four-cell experiment several times with randomized run order before treating the percentages as expected savings.

The follow-up [cross-language calculator benchmark](calculator/RESULTS.md) found perfect functionality across 24 implementations but a different efficiency profile: RTK helped the standard arm, while Compact increased tool calls and total tokens.

## Rollouts

- Standard + RTK: `019f5656-3795-7a22-8d6d-fac1d0cb2007`
- Compact + RTK: `019f5656-3bff-7a10-8fb6-e0c04a415898`
- Standard direct: `019f5666-17b1-7f20-81ed-0f27560581a6`
- Compact direct: `019f5666-1c7e-7100-a3e3-b5464e9edefa`
