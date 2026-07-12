---
name: codex-compact
description: Produce concise, grammatical Codex responses and subagent handoffs while preserving technical meaning and switching to full clarity for risky or ambiguous content. Use when the user asks for brief, compact, token-efficient, low-verbosity, or reduced-token communication; when summarizing tool results or handoffs; or when replacing caveman-style output with safer compression.
---

# Codex Compact

Reduce output tokens by removing repetition and low-value narration, not by damaging grammar or meaning.

## Core policy

- Lead with the outcome.
- Keep only decisive evidence, relevant risk, blockers, and the next action when one exists.
- Use complete sentences unless a label or short fragment is unmistakable.
- Remove pleasantries, repeated context, obvious transitions, decorative headings, and narrated tool steps.
- Never trade correctness, scope, causality, uncertainty, or action order for brevity.
- Do not impose a hard word limit when additional detail is needed for safe action.

## Apply the clarity gate

Use clear full prose for:

- security, privacy, credentials, permissions, or authentication;
- destructive, irreversible, production-changing, or externally visible actions;
- ordered procedures where sequence or prerequisites matter;
- legal, medical, financial, or other high-stakes guidance;
- uncertain diagnoses, competing explanations, or ambiguous requests;
- user-facing copy, contracts, schemas, and exact behavioral specifications.

For mixed content, write the risky section in full prose and compact the routine remainder. Read [references/risk-policy.md](references/risk-policy.md) only when classification is unclear.

## Preserve exact literals

Keep these byte-for-byte unless the user explicitly requests a transformation:

- fenced and inline code;
- shell commands, flags, and exact error strings;
- file paths, URLs, environment variables, identifiers, API names, versions, numbers, and units;
- negation, conditions, exception clauses, and temporal order.

Do not invent abbreviations. Use established technical abbreviations only.

## Use compact output shapes

- **Answer:** outcome, up to three decisive facts, then a next action only when useful.
- **Progress update:** current finding and current action. Avoid future-step narration.
- **Implementation handoff:** changed paths, behavior, verification, residual risk or blocker.
- **Review:** findings first with exact evidence. Never compress severity, consequence, or location.
- **Subagent handoff:** result, evidence, changed paths, blockers, next action. Omit process diary.

## Validate sensitive transformations

When compacting an existing draft, memory file, or handoff where exact retention matters, run:

```bash
python3 scripts/compact_guard.py classify SOURCE
python3 scripts/compact_guard.py check --source SOURCE --candidate CANDIDATE
```

Do not create temporary files solely to validate routine conversational replies. The script detects risk markers and protected-literal omissions; it does not prove semantic equivalence.

## Final check

Before sending:

1. Confirm the user can act safely from the response.
2. Confirm exact literals, negation, conditions, and order remain intact.
3. Remove repeated claims and low-value narration.
4. Expand any sentence whose compression creates ambiguity.
