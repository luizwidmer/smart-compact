# Smart Compact policy iteration

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
| v4 pipeline | 434 | 5 | 78.3% | 6/6 | No |
| v5 proof budget | 299 | 8 | 65.2% | 6/6 | Yes |
| v6 harness profile | 362 | 11 | 52.2% | 6/6 | No |

The projection is a trace-based heuristic, not a token simulation. V2 was initially selected because it targeted the observed expansion without imposing a hard operational cap.

## Single-arm live validation

Only v2-adaptive was rerun. Existing Standard + RTK and prior Compact + RTK results were reused.

| Metric | Standard + RTK | Previous Smart Compact + RTK | v2 Smart Compact + RTK |
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

## Luna/high regression and recovery

V2 did not generalize to Luna/high: it increased total tokens 23.6% with RTK and 36.6% without it. V4 and v5 narrowed the workflow further, then v6 moved stable controls into a native Codex profile.

| Arm | Correctness | Total tokens | Tool calls | Wall time | Disposition |
|---|---:|---:|---:|---:|---|
| Luna high Standard + RTK | 240/240 | 698,797 | 16 | 386.136s | Reused baseline |
| Luna high v2 + RTK | 240/240 | 863,844 | 22 | 553.957s | Regression |
| Luna high v4 + RTK | 240/240 | 861,606 | 20 | 396.272s | Scope spill |
| Luna high v5 + RTK | 240/240 | 563,731 | 16 | 377.643s | RTK-only candidate |
| Luna high v6 profile, initial | 240/240 | 294,264 | 10 | 205.474s | Excluded: partial RTK |
| Luna high v6 profile + strict RTK | 240/240 | 193,312 | 7 | 225.323s | Promoted |
| Luna high Standard direct | 240/240 | 727,106 | 17 | 488.461s | Reused baseline |
| Luna high v2 direct | 240/240 | 992,922 | 23 | 476.854s | Regression |
| Luna high v4 direct | 240/240 | 622,106 | 15 | 408.602s | Candidate |
| Luna high v5 direct | 239/240 | 774,828 | 18 | 551.590s | Correctness failure |

Strict v6 reduced total tokens 72.3%, tool calls 56.2%, and wall time 41.6% versus Luna high Standard + RTK. Its independent 240-case conformance pass, scope audit, and 5/5 RTK shell-command audit were clean.

The initial v6 result was functionally correct but its benchmark prompt did not restate the active RTK requirement. Five of eight submitted shell commands bypassed RTK, so the arm was excluded and regenerated from an empty target root. The same audit-and-rerun rule was applied to SOL/high, SOL/medium, and Luna/max.

## Cross-model strict-RTK validation

| Model / effort | Standard + RTK | V6 profile + RTK | Savings | Tool calls | Wall time |
|---|---:|---:|---:|---:|---:|
| SOL / medium | 243,831 | 109,223 | 55.2% | 9 → 4 | 162.620s → 110.205s |
| SOL / high | 425,765 | 207,227 | 51.3% | 12 → 7 | 344.427s → 161.519s |
| Luna / high | 698,797 | 193,312 | 72.3% | 16 → 7 | 386.136s → 225.323s |
| Luna / max | 936,461 | 188,849 | 79.8% | 19 → 6 | 649.303s → 327.849s |
| **Aggregate** | **2,304,854** | **698,611** | **69.7%** | **56 → 24** | **1,542.486s → 824.896s** |

All eight paired arms passed 240/240. The final new-arm report passed 1,200/1,200, and the persisted traces passed 93/93 RTK shell-command checks. The fail-closed audit is now preserved in `scripts/rtk_trace_audit.py`.

## Decision

Promote v6-harness-profile. Keep v1 through v5 as experiment artifacts. The promoted skill has no hard call budget; the optional native profile controls visible verbosity, stored tool-output size, reasoning summaries, and lossless operational compaction. Do not attempt grammar-stripped input or hidden-reasoning rewrites.

## Rollout

- v2 Smart Compact + RTK: `019f568b-6770-7e82-80e2-41405288c154`
- excluded initial v6 Luna high profile: `019f57d3-f20e-7223-895c-f65171a68a54`
- strict v6 SOL medium profile + RTK: `019f57f1-42d9-7570-aa26-99b1c2b4dc4b`
- strict v6 SOL high profile + RTK: `019f57f1-6a38-74f1-9455-3eb5380ada8f`
- strict v6 Luna high profile + RTK: `019f57f8-40f3-79c1-876d-0124fa1f4243`
- strict v6 Luna max profile + RTK: `019f57f1-464f-7b22-95dd-69a3a3dc7bca`
