---
name: smart-compact-profile-picker
description: Use when the user wants to list or optimize Codex profiles or create a new Codex app task with a selected profile.
---

# Smart Compact Profile Picker

Use `smart_compact_list_profiles` when the user only wants to inspect public profiles.

Use `smart_compact_recommend_profile` for a read-only V9 recommendation. Supply all four optimizer inputs:

- `routingMode`: `auto_spark` or `no_spark`
- `taskShape`: `implementation`, `migration`, `handoff`, or `general`
- `modelFamily`: `sol`, `luna`, or `other`
- `effort`: `medium`, `high`, `xhigh`, `max`, or `other`

Use `general`, `other`, or both when the corresponding fact is unknown; do not invent a measured match. The optimizer may return native Codex, the internal frozen v8-compatible lane, minimal V9, or V9 Spark. V6 and V8 are retired as manual product choices, and internal lanes must not be offered as standalone public profiles.

Use `smart_compact_start_optimized_task` when the user wants the recommendation enacted in a new task. Pass the current absolute workspace path unless the user supplied another one, plus the same four optimizer inputs. Only `auto_spark` + implementation + Luna/max enables the Spark lane. Every other selected lane disables multi-agent support before inference. Native means no profile instructions; it is still a valid optimized selection.

Native adds no optimizer-selected profile, but user-owned global Codex configuration still applies. Do not claim that the tool erased global instructions or reproduced an isolated benchmark environment.

Use `smart_compact_start_task` for manual public-profile selection. Pass `profileId` to create the empty task directly, including on clients without the in-app form. Without `profileId`, the tool opens the form. Both start tools return a `codex://threads/...` link.

Never claim the current task's profile changed. A profile is selected only when the new task is created. Do not copy or start the current prompt in the new task unless a future tool explicitly supports that behavior.
