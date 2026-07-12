# Compact policy iteration

Date: 2026-07-12

## Diagnosis

The accepted calculator Compact + RTK trace used 23 tool calls versus 12 for Standard + RTK. Avoidable expansion included three planning updates, fragmented initial inspection, separate error-case test batches, and duplicate scope audits.

## Offline candidates

The previous 23-call trace was replayed as a categorized workflow. Static policy size used `o200k_base`; safety checks required literal preservation plus explicit escapes for security, destructive, ambiguous, failing, and verification-sensitive work.

| Version | Policy tokens | Projected calls | Projected call reduction | Safety | Hard budget |
|---|---:|---:|---:|---:|---:|
| v0 original | 653 | 23 | 0.0% | 6/6 | No |
| v1 minimal | 180 | 23 | 0.0% | 6/6 | No |
| v2 adaptive | 343 | 10 | 56.5% | 6/6 | No |
| v3 hard budget | 165 | 8 | 65.2% | 6/6 | Yes |

The projection is a trace-based heuristic, not a token simulation. V2 was selected because it targeted the observed expansion without imposing a hard operational cap.

## Single-arm live validation

Only v2-adaptive was rerun. Existing Standard + RTK and prior Compact + RTK results were reused.

| Metric | Standard + RTK | Previous Compact + RTK | v2 Compact + RTK |
|---|---:|---:|---:|
| Correctness | 240/240 | 240/240 | 240/240 |
| Total tokens | 425,765 | 708,437 | 294,388 |
| Input tokens | 411,398 | 693,938 | 282,138 |
| Cached input | 381,696 | 658,432 | 261,376 |
| Uncached input | 29,702 | 35,506 | 20,762 |
| Output tokens | 14,367 | 14,499 | 12,250 |
| Reasoning output | 2,220 | 1,756 | 2,168 |
| Tool calls | 12 | 23 | 10 |
| Wall time | 344.427s | 368.727s | 310.427s |
| Source artifact | 737 lines | 765 lines | 668 lines |

V2 used 30.9% fewer total tokens than Standard + RTK and 58.4% fewer than the previous Compact + RTK policy. It also reduced uncached input by 30.1%, output by 14.7%, tool calls by 16.7%, and wall time by 9.9% relative to Standard + RTK while preserving perfect functionality.

## Decision

Promote v2-adaptive. Keep v1 and v3 as experiment artifacts. V1 does not address workflow expansion; v3's hard budget adds avoidable correctness pressure for only two projected calls of additional benefit.

## Rollout

- v2 Compact + RTK: `019f568b-6770-7e82-80e2-41405288c154`
