# Smart Compact optimizer

The experimental optimizer selects one tested instruction lane before a Codex task is created. It does not blend prompts at runtime and cannot change an active task's profile.

## Lanes

| Lane | Use |
| --- | --- |
| `smart-compact-v8` | Automatic Spark routing |
| `smart-compact-v8-natural` | No-Spark migration, handoff, and general work |
| `smart-compact-v6` | No-Spark path-disjoint implementation work |

The first-match rules are machine-readable in [`selection.json`](selection.json). Task shapes are:

- `implementation`: path-disjoint implementations of the same contract.
- `migration`: repetitive path-disjoint edits under one shared migration contract.
- `handoff`: tightly coupled parent work with at most one externally supplied handoff.
- `general`: use when the task does not clearly match a measured shape.

Automatic routing selects terse v8. This direction is informed by the harness result, but production auto-routing intentionally omits the harness's Spark-availability prompt and is not included in the replay metric. No-Spark implementation selects frozen v6 on the four-setting aggregate; other no-Spark work selects natural v8. The command and plugin apply `multi_agent` as configuration before inference, so enforcement consumes no model tokens. Forced Spark remains an evaluation-only harness treatment because reproducing it with prompt instructions would add tokens and would not match the measured arm.

Command output is refused when the installed named profile is missing or differs from its bound hash. Optimized plugin starts use the bundled frozen profile directly, so a same-named custom file cannot silently replace the measured treatment.

## Evidence boundary

Replaying the no-Spark rules over 21 already observed cells chooses 3,430,364 parent tokens versus 4,509,801 for all-terse v8, a counterfactual reduction of 1,079,437 tokens (23.935%). This is a development replay, not fresh inference, not a variance estimate, and not a release metric. It can be optimistic because measured task shapes informed the rules.

The natural profile is byte-identical to the frozen verbose treatment. The decision table binds the release summary, verbose comparison, and all three profile hashes. Fresh validation should compare the selector package against all-terse v8 on a smaller held-out matrix before making it the default or publishing the replay as a release metric.
