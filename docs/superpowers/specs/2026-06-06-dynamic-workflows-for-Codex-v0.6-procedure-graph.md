# Dynamic Workflows For Codex v0.6 Procedure Graph Spec

## Goal

Make workflow specs express how a workflow proceeds, not only which workers
exist. A saved spec should include a procedure graph with triggers, stages,
verification gates, and failure behavior so Codex can treat it as a reusable
dynamic workflow protocol.

## Why

The current v2 spec envelope stores useful metadata and constraints, but the
execution structure still lives mostly inside `WorkflowPlan.work_units`. That
is enough for deterministic runtime tests, but it is too flat for a
Superpowers-style workflow skill. A stronger spec needs to say:

- When this workflow should be used.
- Which stages run together.
- Which verification gate closes a stage.
- What happens when a stage fails.
- Which artifacts the workflow should leave behind.

## Scope

Add a v3-compatible procedure graph to `WorkflowSpecBundle`:

- `schema_version`: saved specs use `"3"`.
- `procedure.mode`: `single-stage`, `fan-out`, `sequence`, or `guarded`.
- `procedure.triggers`: user-intent phrases that should activate the workflow.
- `procedure.stages`: ordered stages with work unit references, gate policy,
  and failure behavior.
- `procedure.final_artifacts`: expected outputs after synthesis.

The loader remains backward compatible:

- v1 plan-root specs still load.
- v2 envelope specs without `procedure` still load.
- Loaded v2 bundles receive a generated default procedure derived from the
  embedded plan.

## Stage Rules

Each stage includes:

- `id`: stable identifier.
- `purpose`: why the stage exists.
- `work_unit_ids`: references to existing `WorkflowPlan.work_units`.
- `gate`: `all_required_verified`, `any_verified`, or `manual_review`.
- `on_failure`: `stop`, `continue`, or `require_human`.

Validation rules:

- Every referenced work unit id must exist in the plan.
- A work unit id may appear in only one stage.
- Every plan work unit must be covered by a stage.
- `procedure.stages` must be non-empty when `procedure` is present.

## Defaults

Generated procedures should match current plan behavior:

- `review`: fan-out stage covering all review work units.
- `debug`: fan-out stage covering all hypothesis investigators.
- `plan`: single-stage planner workflow.
- `migrate`: guarded sequence with inventory first, then patch planning and
  verification.

## Non-Goals

- Do not change runtime execution order yet.
- Do not run real Codex workers.
- Do not add a visual editor or YAML parser.
- Do not remove v1 or v2 compatibility.

## Acceptance Criteria

- `save_workflow_spec` writes a v3 envelope with a procedure graph.
- `load_workflow_spec_bundle` loads v2 envelopes without `procedure` and fills
  a default procedure.
- Invalid procedure references fail validation.
- Existing `load_workflow_spec` still returns the embedded `WorkflowPlan`.
- README/evaluation docs describe v3 procedure graph behavior.
- Full test suite passes.
