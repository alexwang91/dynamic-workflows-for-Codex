# Dynamic Workflows For Codex v0.11 Human Approval Gates Spec

## Goal

Make human approval gates executable runtime behavior instead of only metadata
inside workflow specs.

## Why

v0.10 can dynamically generate staged workflow specs. Some generated or static
specs already contain `manual_review` gates and `require_human` failure
behavior, especially guarded migration plans. Today those fields are only
interpreted as verification gate metadata. v0.11 should let the runtime pause
before human-gated stages, persist that pause, and resume only when the user
explicitly approves.

## Scope

Add runtime support for human-gated stages:

- A stage requires human approval when `stage.gate == "manual_review"` or
  `stage.on_failure == "require_human"`.
- Without explicit approval, the runtime stops before executing that stage.
- The run state persists `pending_human_approval` with the stage id.
- Synthesis status becomes `waiting_for_human`.
- CLI exits non-zero and reports the pending stage.
- `cdw resume <run-id> --approve-human-gates` allows the runtime to pass the
  currently pending human-gated stage.

## Non-Goals

- Do not add an interactive prompt UI.
- Do not implement partial approval per work unit.
- Do not make fake mode bypass human approval automatically.
- Do not change the v3 workflow schema format.
- Do not execute write-heavy work without an explicit CLI approval flag.

## Design

Extend `RunState` with:

```python
pending_human_approval: str | None = None
```

Extend `SynthesisReport.status` with:

```python
"waiting_for_human"
```

Runtime procedure execution checks each stage before worker dispatch. If the
stage requires human approval and no matching approval is already pending, it
saves the pending stage and stops. If `approve_human_gates` is true on resume,
it clears only the matching pending approval and executes that stage normally.
Later human-gated stages must pause again before they can be approved.

CLI adds `--approve-human-gates` to `resume`. The flag is explicit and auditable
in shell history, and fresh runs cannot pre-approve unseen human gates.

## Acceptance Criteria

- A workflow with a `manual_review` stage pauses before that stage without
  running its workers.
- The paused run state includes `pending_human_approval`.
- CLI returns non-zero and reports `waiting for human approval`.
- `resume <run-id> --approve-human-gates` continues the pending stage.
- Approval only releases the currently pending stage; later human gates pause
  again.
- Existing non-human-gated workflows continue to pass.
- Full tests pass.
