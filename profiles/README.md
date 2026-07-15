# Smart Compact profiles

Smart Compact V9 is the only current product generation. Its optimizer may select four lanes:

| Lane | File | Visibility | Purpose |
| --- | --- | --- | --- |
| `native` | No profile file | Internal optimizer lane | Run default Codex with multi-agent disabled and no added profile instructions |
| `v9` | `smart-compact-v9.config.toml` | Public | 259-byte minimal local contract |
| `v9-v8` | `smart-compact-v9-v8.config.toml` | Internal | Byte-identical frozen v8-compatible treatment under a V9-only ID |
| `v9-spark` | `smart-compact-v9-spark.config.toml` | Internal | 769-byte measured Spark treatment |

`smart-compact.config.toml` is the unversioned alias for the public `smart-compact-v9` profile.

The native lane is selected by omitting `--profile`; it still passes `--disable multi_agent` before inference. The `v9-v8` lane preserves measured V8 behavior but does not restore V8 as a public or manually supported product. Only `v9-spark` enables multi-agent execution.

V6, V7, V8, natural-language prototypes, and earlier V9 prototypes remain archived for benchmark verification and upgrade cleanup. They are not selectable product versions.
