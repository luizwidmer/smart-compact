---
name: smart-compact-profile-picker
description: Use when the user wants to list Codex profiles or create a new Codex app task with a selected profile.
---

# Smart Compact Profile Picker

Use `smart_compact_list_profiles` when the user only wants to inspect available profiles.

Use `smart_compact_start_task` when the user wants a new task. Pass the current absolute workspace path unless the user supplied another one. The tool opens an in-app form, creates an empty task with the selected profile, and returns a `codex://threads/...` link.

Never claim the current task's profile changed. A profile is selected only when the new task is created. Do not copy or start the current prompt in the new task unless a future tool explicitly supports that behavior.
