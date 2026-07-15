---
name: smart-compact-v9
description: Reduce parent-model token use with a minimal adaptive Spark routing contract while preserving correctness and safety.
---

# Smart Compact v9

```text
objective=parent_tokens:min;guard=correctness+safety+scope
preserve=numbers+negation
delegate.when=bounded+independent+material_parent_work_saved
delegate.do=spawn:spark_worker,before_parent_reads_partition
workers=smallest_useful,cap:none,parallel_disjoint
brief=partition_ids,exclusive_paths,task,result_contract
parent=disjoint_only,integrate_once,decide+verify,drain_all
local=tiny,sequential,overlap,ambiguous,security_sensitive,destructive,external_state,unverifiable,spark_unavailable
return=outcome,paths,verification,failures,blockers,risk
```
