# Smart Compact

[Smart Compact](https://github.com/luizwidmer/smart-compact) is a Codex package that reduces parent-model token use while preserving task correctness, safety, and scope.

V9 is the sole current product generation. It treats every instruction state as a cost: before a task starts, the optimizer chooses native Codex, a frozen v8-compatible state, the minimal v9 state, or the v9 Spark state. V6-v8 remain benchmark history, not public product choices.

Parent tokens are the optimization target. Spark child tokens are telemetry only.

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/luizwidmer/smart-compact/main/install.sh | sh -s -- --version v9
```

From a checkout:

```bash
git clone https://github.com/luizwidmer/smart-compact.git
cd smart-compact
./install.sh --version v9
```

The installer also supports `--dry-run`, `--force`, `--no-spark`, `--no-profile`, `--no-plugin`, and `--make-default`. Restart Codex or open a new task after installation.

For evidence-aligned state-aware routing, leave `--make-default` off. Promoting V9 into the global Codex config means the `native` lane still inherits that global state; the optimizer does not erase user-owned global instructions.

## Use

- Default alias: `codex --profile smart-compact`
- Versioned profile: `codex --profile smart-compact-v9`
- Existing task skill: `$smart-compact` or `$smart-compact-v9`
- Codex app: select `@Smart Compact`

Ask the optimizer for the measured route before creating a task:

```bash
python3 scripts/select_optimizer_profile.py \
  --routing-mode auto_spark \
  --task-shape implementation \
  --model-family luna \
  --effort max \
  --format command
```

The four lanes are:

| Lane | Added instruction state | Use |
| --- | --- | --- |
| `native` | None | Avoid profile-state cost where native Codex won |
| `v9-v8` | Exact frozen v8-compatible profile | Preserve measured v8 strengths under the V9 optimizer |
| `v9` | 259-byte minimal local contract | Local handoff, general, and conservative fallback work |
| `v9-spark` | 769-byte offload contract | Only the measured Luna/max implementation win |

Only `v9-spark` enables multi-agent execution. It has no fixed worker cap and requests the smallest useful worker set.

## Official benchmark results

The official suite covers Calculator, Relay, and SDK Migration at Sol medium/high and Luna xhigh/max. Parent-token counts are lower-is-better.

| Benchmark | Model | Effort | Standard | V6 | V8 | V9 parent (lane) | V9 saved vs Standard | V9 saved vs V6 | V9 saved vs V8 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Calculator | Sol | medium | 448,551 | 147,287 | 114,812 | 114,812 (`v9-v8`) | 333,739 | 32,475 | 0 |
| Calculator | Sol | high | 293,003 | 173,915 | 271,642 | 271,642 (`v9-v8`) | 21,361 | -97,727 | 0 |
| Calculator | Luna | xhigh | 420,095 | 336,471 | 409,852 | 409,852 (`v9-v8`) | 10,243 | -73,381 | 0 |
| Calculator | Luna | max | 559,838 | 655,352 | 548,078 | 463,836 (`v9-spark`) | 96,002 | 191,516 | 84,242 |
| Relay | Sol | medium | 156,702 | 163,259 | 168,563 | 138,871 (`v9`) | 17,831 | 24,388 | 29,692 |
| Relay | Sol | high | 140,322 | 138,970 | 179,239 | 115,276 (`v9`) | 25,046 | 23,694 | 63,963 |
| Relay | Luna | xhigh | 251,921 | 499,673 | 483,667 | 281,655 (`v9`) | -29,734 | 218,018 | 202,012 |
| Relay | Luna | max | 156,912 | 163,112 | 140,026 | 140,026 (`v9-v8`) | 16,886 | 23,086 | 0 |
| SDK Migration | Sol | medium | 114,900 | 101,684 | 132,155 | 114,900 (`native`) | 0 | -13,216 | 17,255 |
| SDK Migration | Sol | high | 116,482 | 229,494 | 136,167 | 136,167 (`v9-v8`) | -19,685 | 93,327 | 0 |
| SDK Migration | Luna | xhigh | 248,170 | 561,434 | 203,151 | 203,151 (`v9-v8`) | 45,019 | 358,283 | 0 |
| SDK Migration | Luna | max | 231,586 | 190,453 | 217,578 | 217,578 (`v9-v8`) | 14,008 | -27,125 | 0 |
| **Official 12 total** | **2 models** | **4 efforts** | **3,138,482** | **3,361,104** | **3,004,930** | **2,607,766** | **530,716 (16.910%)** | **753,338 (22.413%)** | **397,164 (13.217%)** |

Negative savings mean V9 used more parent tokens in that cell. All 12 selected official cells completed the task correctly.

The state-aware selection matters. Enforcing one uniform V9 state used 3,817,102 parent tokens; the definitive router used 2,607,766, saving 1,209,336 tokens (31.682%). The selected official Spark route spawned one worker. Its 273,944 child tokens are reported separately and do not consume the optimized parent allowance.

The four added real-world cases also passed:

| Suite | V6 parent | V8 parent | V9 parent | V9 saved vs V6 | V9 saved vs V8 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Fresh additions (4) | 1,029,924 | 468,581 | 462,901 | 567,023 (55.055%) | 5,680 (1.212%) |
| **Combined official + fresh (16)** | **4,391,028** | **3,473,511** | **3,070,667** | **1,320,361 (30.070%)** | **402,844 (11.598%)** |

All 16 selected source cells were task-correct. This is a post-matrix deployable hybrid selection, not a blinded confirmation run. During the official run, workspace collisions prevented nine cells from starting; recovery ran only those nine non-attempts, so no real inference cell was repeated. One recovery cell had an RTK-only protocol miss but still received full task credit.

See [RESEARCH.md](RESEARCH.md) for routing, provenance, and limitations.

## Validate

```bash
python3 scripts/verify_v9_definitive.py
python3 scripts/verify_optimizer_package.py
python3 -m unittest discover -s tests -v
```

## License

Copyright 2026 Luiz Widmer. Licensed under the [Apache License 2.0](LICENSE); see [NOTICE](NOTICE).
