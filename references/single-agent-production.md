# Source ownership and resumable production

Use this reference for resumed work, incremental repair or deeper editions. For healthy ordinary generation, [standard fast path](production-flow.md) is the entry point.

One agent owns destination content; independent reads and downloads may run concurrently. Delegate only when explicitly requested and permitted. Preserve the selected model. [Pipeline](research-and-profile-pipeline.md) defines canonical pack ownership and the controller’s phase dependencies.

## Continue from existing work

Read the brief, persisted state and current task rather than all prior output. Preserve useful research and unchanged evidence. The controller initializes and seeds conservative language/preparation drafts; review destination differences before clearing `_draft`. Use the relevant scaffold for an unfamiliar shape rather than reconstructing it from validator code.


## Repair a failure

Inspect the actual error and smallest relevant data or script. Correct its cause, rerun the affected operation and continue dependent work. If the same method fails repeatedly, change the approach based on the error; do not weaken acceptance or restart unrelated completed work. Use [runner setup](runner-command-contract.md) for host invocation errors, [fetch recovery](fetch-recovery.md) for source failures and [gateway recovery](gateway-failure-recovery.md) for platform failures.

[Rendering](rendering-and-assets.md) owns media review; [release validation](release-validation.md) owns QA. Avoid restating either protocol in a task prompt. A status command, compilation or script timer does not establish visual correctness or total generation time.

## Incremental validation

`plan_incremental_validation.py` tracks copy, media declarations and runtime changes. Use it to retain valid evidence for unchanged inputs and identify checks needed for changed inputs. The plan is not proof that checks passed. Report timing only from actual observations, including rework; never infer token savings from elapsed time.

Complete the requested repair and its affected checks in the active task. Stop for missing essential input, a real access boundary or the defined review state, not merely because an initial patch is ready.
