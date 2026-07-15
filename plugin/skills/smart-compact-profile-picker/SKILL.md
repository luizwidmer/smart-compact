---
name: smart-compact-profile-picker
description: Use when the user wants to list or optimize Codex profiles or create a new Codex app task with a selected profile.
---

# Smart Compact Profile Picker

Use `smart_compact_list_profiles` when the user only wants to inspect available profiles.

Use `smart_compact_recommend_profile` when the user wants a read-only token-saving recommendation. Supply `no_spark` or `auto_spark` plus the closest task shape; use `general` rather than guessing.

Use `smart_compact_start_optimized_task` when the user wants the recommendation enacted in a new task. Pass the current absolute workspace path unless the user supplied another one. This tool uses the bundled frozen profile and enables or disables multi-agent support through task configuration before inference; it does not add routing instructions to the prompt.

Use `smart_compact_start_task` for manual profile selection. Pass `profileId` to create the empty task directly, including on clients without the in-app form. Without `profileId`, the tool opens the form. Both start tools return a `codex://threads/...` link.

Never claim the current task's profile changed. A profile is selected only when the new task is created. Do not copy or start the current prompt in the new task unless a future tool explicitly supports that behavior.
