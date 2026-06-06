# Dynamic Workflows For Codex v0.6 Runtime Procedure Execution Spec

## Goal

Make the runtime execute workflow specs according to their v3 procedure graph.
`cdw run <workflow-spec>` should use stages, gates, and failure behavior instead
of flattening all work units into a single pass.

## Why

v0.6 added procedure graphs to saved workflow specs. This made specs more
expressive, but runtime execution still followed the flat `WorkflowPlan`
ordering. The next step is to make the graph operational so saved specs behave
like dynamic workflow protocols.

## Scope

Add procedure-aware execution:

- `execute_workflow_bundle(bundle, root, adapter)` executes a
  `WorkflowSpecBundle`.
- `execute_plan(plan, root, adapter)` remains available and wraps the plan in a
  generated default bundle.
- `cdw run <workflow-spec>` loads the full bundle and executes its procedure.
- `RunState` stores the procedure so `resume` can keep the same staged behavior.

## Stage Semantics

For each stage:

- Run missing workers referenced by `stage.work_unit_ids`.
- Verify missing worker results for that stage.
- Evaluate the stage gate.
- If the gate passes, continue to the next stage.
- If the gate fails and `on_failure == "stop"`, stop the workflow and synthesize
  an incomplete result.
- If the gate fails and `on_failure == "continue"`, continue to the next stage
  but keep unresolved findings.
- If the gate fails and `on_failure == "require_human"`, stop the workflow and
  synthesize an incomplete result.

Gate rules:

- `all_required_verified`: all required work units in the stage must have passed
  verification.
- `any_verified`: at least one stage work unit must have passed verification.
- `manual_review`: all stage work units must have passed verification before
  automatic execution may continue.

## Non-Goals

- Do not add real human approval prompts.
- Do not change adapter interfaces.
- Do not consume real Codex quota in tests.
- Do not add stage-level state objects yet; persisted worker and verification
  results remain the source of truth.

## Acceptance Criteria

- A failing `stop` stage prevents later-stage workers from running.
- A failing `continue` stage still allows later-stage workers to run.
- `RunState` persists the procedure used by `execute_workflow_bundle`.
- `resume` preserves staged stop behavior when a saved run contains a
  procedure.
- `cdw run <workflow-spec>` uses the bundle execution path.
- Existing flat plan execution remains compatible.
- Full test suite passes.
