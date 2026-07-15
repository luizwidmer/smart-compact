---
name: smart-compact-v8
description: Minimize parent-model tokens with concise execution and audited work-replacing Spark delegation.
---

# Smart Compact v8

```text
objective=parent_tokens:min
guard=correctness,safety,scope
bounded=plan:none;inspect:required_only;reads:batch_independent;patch:coherent_once;acceptance:verbatim_once;retry:diagnosed_failure_only;status:once;stop
preserve=requirements,commands,paths,identifiers,numbers,values,negation,order
shell.wrapper=literal_every_command_and_retry
delegate.when=bounded+independent+mechanical+work_replacing
delegate.required=spawn_first,before_worker_path_read
workers=smallest_useful;cap:none;multi_partition:true;extra:material_parent_work_or_critical_path
brief=partition_ids_first,exclusive_paths,task,result_contract
parent=disjoint_only;consume_accepted_once;drain_all;owns_decisions+integration+final_acceptance
local=tiny,sequential,overlap,ambiguous,security_sensitive,destructive,external_state,unverifiable
spark_unavailable=local,no_substitution,no_reprobe
return=outcome,changed_paths,decisive_verification,blockers,material_residual_risk
```
