# Smart Compact V9 optimizer

The optimizer selects one deployable state before task creation. It never changes an active task or blends prompts at runtime.

## Inputs

Every selection uses:

- routing mode: `auto_spark` or `no_spark`
- task shape: `implementation`, `migration`, `handoff`, or `general`
- model family: `sol`, `luna`, or `other`
- effort: `medium`, `high`, `xhigh`, `max`, or `other`

```bash
python3 scripts/select_optimizer_profile.py \
  --routing-mode auto_spark \
  --task-shape implementation \
  --model-family luna \
  --effort max \
  --format command
```

## Lanes

| Lane | Profile | Behavior |
| --- | --- | --- |
| `native` | None | Default Codex with multi-agent disabled; zero added instruction state |
| `v9-v8` | `smart-compact-v9-v8` | Exact frozen v8-compatible internal treatment with multi-agent disabled |
| `v9` | `smart-compact-v9` | Minimal local V9 contract with multi-agent disabled |
| `v9-spark` | `smart-compact-v9-spark` | Explicit offload contract with multi-agent enabled |

Only `auto_spark` + implementation + Luna/max selects `v9-spark`. `no_spark` selects `v9-v8` for that setting.

| Shape | Measured setting | Lane |
| --- | --- | --- |
| Implementation | Sol/medium, Sol/high, Luna/xhigh | `v9-v8` |
| Implementation | Luna/max | `v9-spark` under `auto_spark`; otherwise `v9-v8` |
| Migration | Sol/medium | `native` |
| Migration | Sol/high, Luna/xhigh, Luna/max | `v9-v8` |
| Handoff | Luna/max | `v9-v8` |
| Handoff | Every other setting | `v9` |
| General | Every setting | `v9` |
| Implementation or migration | Unmeasured setting | `v9` |

For the native lane, command output is `codex --disable multi_agent`; profile-only output is `codex-default`. All non-Spark lanes disable multi-agent before inference. The Spark lane has no fixed worker cap and asks for the smallest useful set.

Native means the optimizer adds no profile instructions. It still inherits the user's global Codex config, so `--make-default` is intentionally not benchmark-equivalent to the isolated Standard control.

## Evidence

Uniform V9 state enforcement used 3,817,102 official parent tokens. State-aware selection used 2,607,766, saving 1,209,336 (31.682%). The definitive official selection also saved 397,164 parent tokens (13.217%) versus V8 while selecting one Spark worker in total.

The rules are a post-matrix deployable hybrid selection, not blinded confirmation. Machine-readable first-match rules, evidence labels, and bound hashes are in [`selection.json`](selection.json). Command output is refused when an installed profile differs from its bound hash.
