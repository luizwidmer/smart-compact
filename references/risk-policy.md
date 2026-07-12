# Risk policy

Use this reference only when the clarity gate in `SKILL.md` is uncertain.

## Compression decisions

| Content | Mode | Required detail |
|---|---|---|
| Routine status, summary, or handoff | Compact | Outcome, evidence, blocker, next action |
| Code review finding | Compact but exact | Severity, path or line, consequence, fix direction |
| Security, credentials, or permissions | Full prose | Scope, exposure, consequence, safe handling |
| Destructive or irreversible action | Full prose | Target, effect, reversibility, backup or recovery |
| Ordered procedure | Full prose or numbered steps | Preconditions, order, checkpoints, failure behavior |
| Uncertain diagnosis | Full prose | Known facts, inference, uncertainty, verification |
| User-facing copy or contract | Requested style | Exact meaning and required terminology |
| Legal, medical, or financial guidance | Full prose | Limits, uncertainty, authoritative verification |

## Safe removals

- Pleasantries and filler.
- Repeated task context.
- Narration of obvious tool calls.
- Duplicate conclusions.
- Decorative headings for short answers.
- Multiple examples proving the same point.

## Unsafe removals

- Negation such as `not`, `never`, `without`, or `cannot`.
- Conditions such as `if`, `unless`, `only`, or `except`.
- Units, versions, counts, dates, and thresholds.
- Actors, targets, ownership, or affected scope.
- Preconditions, ordering, rollback, or verification steps.
- Evidence supporting a diagnosis or review finding.
- Uncertainty labels that distinguish fact from inference.

## Escalation rule

When uncertain whether compression is safe, keep full prose. A few extra tokens cost less than an ambiguous instruction.
