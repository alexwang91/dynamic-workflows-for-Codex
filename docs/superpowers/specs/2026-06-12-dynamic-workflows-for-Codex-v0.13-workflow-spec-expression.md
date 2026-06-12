# Dynamic Workflows For Codex v0.13 Workflow Spec Expression Spec

## Goal

Make v3 workflow specs express stronger stage relationships, artifact flow, and
write-heavy migration boundaries without replacing the existing runtime.

## Why

v0.12 can plan, run, pause, resume, and inspect workflows, but procedure stages
still only say which workers run together. That is enough for simple fan-out
and guarded migration planning, but it is too weak for Claude/Superpowers-style
dynamic workflows where later stages should explicitly depend on earlier
verified outputs.

v0.13 adds a small amount of structure:

- Stage dependencies: later stages can name prerequisite stage ids.
- Artifact flow: stages can declare artifacts they consume and produce.
- Stage write policy: stages can declare whether they are read-only, guarded,
  or write-heavy.

## Scope

Extend `WorkflowStage` with:

```python
depends_on: list[str] = []
consumes: list[str] = []
produces: list[str] = []
write_policy: Literal["read-only", "guarded", "write-heavy"] = "read-only"
```

Validation rules:

- Stage ids must be unique.
- `depends_on` entries must reference earlier stage ids.
- A stage cannot depend on itself.
- `consumes` entries must be produced by a stage listed in `depends_on`.
- `guarded` and `write-heavy` stages must use `manual_review` or
  `require_human`.
- `write-heavy` stages must depend on an earlier stage and consume at least one
  artifact.
- Top-level `write-heavy` specs must require human approval and include at
  least one human-gated stage.

Runtime rules:

- A stage does not run until every `depends_on` stage has passed its gate.
- If a dependency is not passed, execution stops before the blocked stage.
- Existing ordered stage behavior remains unchanged for specs without
  dependencies.

Migration spec generation:

- `migration-inventory` is read-only and produces `migration inventory`.
- `migration-plan-review` depends on `migration-inventory`, consumes
  `migration inventory`, produces `guarded patch plan` and `migration risk
  review`, and is `guarded`.
- The migration spec remains top-level `write-heavy` with human approval.

Dynamic planner contract:

- The Codex CLI planner output schema includes the new stage fields.
- The planner prompt tells Codex to express dependencies and artifact flow.
- Missing new fields remain accepted by Pydantic defaults for older specs.

## Non-Goals

- Do not build a parallel DAG scheduler.
- Do not execute actual write-heavy patches.
- Do not add path-level filesystem enforcement yet.
- Do not require legacy v2/v3 specs to be rewritten.
- Do not add interactive prompts.

## Acceptance Criteria

- Workflow specs reject unknown, self, or out-of-order stage dependencies.
- Workflow specs reject consumed artifacts that are not produced by declared
  dependencies.
- Runtime stops before a dependent stage when the prerequisite stage fails.
- Generated migration specs include explicit dependencies, artifacts, and
  guarded write policy.
- Dynamic planner fake and output schema include the new stage fields.
- Existing v1/v2/v3 compatibility tests still pass.
- Full tests pass.
