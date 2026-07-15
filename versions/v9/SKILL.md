---
name: smart-compact-v9
description: Minimize parent-model token use with a tiny local-first execution contract; preselected Spark routing is available through the optimizer.
---

# Smart Compact v9

```text
objective=parent_tokens:min;guard=correctness+safety+scope
preserve=numbers+negation
escalate=security,destructive,ambiguous
routing=local;delegation=forbidden
execute=inspect_needed,batch_reads,coherent_patch,acceptance_once,retry_diagnosed
return=outcome,paths,verification,failures,blockers,risk
```
