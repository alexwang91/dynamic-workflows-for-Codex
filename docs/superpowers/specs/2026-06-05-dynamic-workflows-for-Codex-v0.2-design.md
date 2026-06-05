---
title: dynamic-workflows-for-Codex v0.2 Design
date: 2026-06-05
status: approved-for-planning
---

# dynamic-workflows-for-Codex v0.2 Design

## 1. Alignment Check

The original goal was to recreate Claude-style dynamic workflows for Codex as an external orchestration runtime, not as a prompt library or a skill-only imitation.

v0.1 stayed aligned with that goal:

- Runtime state lives outside the chat context in `.cdw/runs/<run-id>/state.json`.
- The runtime owns worker execution, verification, and synthesis ordering.
- Work is represented with typed Pydantic schemas.
- Codex MCP execution is isolated behind an adapter.
- The live adapter constructs a `codex mcp-server` stdio server through the OpenAI Agents SDK.

Known v0.1 gaps:

- Workflow plans are typed Python objects, but not yet reusable workflow specs.
- Runs are inspectable, but not resumable.
- No Codex skill/plugin packaging exists yet.
- Write-heavy workflows are intentionally disabled.

v0.2 should close these gaps without drifting into a broad platform rewrite.

## 2. v0.2 Product Goal

Turn the v0.1 MVP into a more faithful dynamic workflow harness by adding:

- Resumable runs.
- File-backed workflow specs.
- A repo-local Codex skill wrapper.
- A safe first write-heavy migration workflow.

The target user experience is:

```bash
cdw plan "Review this branch" --save-spec review.workflow.json
cdw run review.workflow.json --adapter fake
cdw resume <run-id> --adapter fake
cdw migrate "Rename User model to Account" --adapter fake
```

## 3. Scope

### In Scope

Commands:

- `cdw run <workflow-spec>`: execute a saved workflow spec.
- `cdw resume <run-id>`: continue an incomplete run from persisted state.
- `cdw migrate <request>`: create and execute a guarded write-heavy workflow.
- `cdw install-skill`: install or refresh a repo-local Codex skill under `.agents/skills/dynamic-workflows-for-Codex/`.

Workflow spec:

- JSON file format backed by the existing `WorkflowPlan` schema.
- Versioned with `schema_version`.
- Can be created by `cdw plan --save-spec <path>`.
- Can be executed by `cdw run <path>`.

Resume:

- Load `.cdw/runs/<run-id>/state.json`.
- Detect missing required worker results.
- Detect missing verifier results.
- Continue from the earliest incomplete phase.
- Never rerun completed worker/verifier phases unless `--rerun` is provided.

Write-heavy migration:

- Add deterministic `migrate` planning.
- Require a worktree strategy before edits.
- In v0.2 fake mode, simulate worker outputs without editing files.
- Live mode prompts must instruct workers to use isolated worktrees or bounded file ownership.
- Synthesis must report merge readiness rather than auto-merging.

Skill wrapper:

- Generate `.agents/skills/dynamic-workflows-for-Codex/SKILL.md`.
- Skill tells Codex when to call `cdw`.
- Skill explicitly says the runtime, not the skill, owns orchestration.
- Skill includes trigger guidance for complex review/debug/migration tasks.

### Out of Scope

- Marketplace plugin publication.
- Real parallel git worktree merge automation.
- Arbitrary Python or JavaScript workflow execution.
- Remote/cloud orchestration.
- UI dashboard.
- Live Codex MCP end-to-end smoke as a required CI test.

## 4. Architecture Changes

### New Modules

```text
src/cdw/
  workflow_spec.py
  resume.py
  skill.py
```

### Modified Modules

`schemas.py`

- Add `schema_version` to `WorkflowPlan`.
- Add `RunPhase` or equivalent run status fields if needed.
- Add `MIGRATE` command enum.

`planner.py`

- Add `migrate` deterministic plan.
- Preserve review/debug behavior.

`runtime.py`

- Split execution into resumable phases:
  - ensure worker results
  - ensure verifier results
  - synthesize
- Make phase methods idempotent.

`state.py`

- Add helpers to list runs and locate run state.
- Keep existing atomic save behavior.

`cli.py`

- Add `run`, `resume`, `migrate`, `install-skill`.
- Add `--save-spec` to `plan`.

## 5. Data Flow

### Save Spec

```text
cdw plan request --save-spec review.workflow.json
  -> planner builds WorkflowPlan
  -> workflow_spec saves validated JSON
  -> optional run state is still created only when execution is requested
```

### Run Spec

```text
cdw run review.workflow.json
  -> workflow_spec loads and validates WorkflowPlan
  -> runtime creates RunState
  -> runtime executes phases
  -> state persists results
```

### Resume

```text
cdw resume <run-id>
  -> state loads RunState
  -> runtime checks completed work_unit_ids
  -> runtime runs only missing workers
  -> runtime checks completed verifier ids
  -> runtime runs only missing verifiers
  -> runtime synthesizes when stop condition is satisfied
```

### Migration

```text
cdw migrate request
  -> planner creates migration work units by slice
  -> runtime executes workers
  -> verifier checks proposed changes or simulated patches
  -> synthesizer reports merge readiness and unresolved conflicts
```

## 6. Safety Rules

Write-heavy workflows require stricter rules than review/debug:

- Workers must have explicit file/module ownership.
- Workers must not edit outside their assigned slice.
- Runtime must not auto-merge parallel edits in v0.2.
- Synthesis reports what is ready, blocked, or needs human review.
- Live mode must mention sandbox and approval policy in worker prompts.

If isolation is unavailable, `migrate` should either:

- run in fake mode,
- produce a plan only,
- or stop with an explicit safety error.

## 7. Testing Strategy

Unit tests:

- Workflow spec save/load round trip.
- CLI `plan --save-spec`.
- CLI `run <spec>` with fake adapter.
- Resume skips completed worker results.
- Resume fills missing verifier results.
- Migration planner creates write-heavy work units with ownership text.
- Skill installer writes valid `SKILL.md`.

Integration tests:

- Fake adapter end-to-end for `run`, `resume`, `migrate`, and `install-skill`.
- Existing v0.1 tests remain green.

Manual checks:

- Run `cdw plan --save-spec`.
- Run `cdw run <spec> --adapter fake`.
- Delete one verifier result from a run state and run `cdw resume <run-id>`.
- Inspect generated `.agents/skills/dynamic-workflows-for-Codex/SKILL.md`.

## 8. Evaluation Checkpoints

v0.2 is successful if:

- A workflow can be saved, shared, and re-run from a file.
- A failed or partial run can continue without duplicating completed work.
- The generated Codex skill clearly delegates orchestration to `cdw`.
- Migration is available but guarded, not reckless.
- The runtime still owns control flow; prompts do not become the control plane.

v0.2 is drifting if:

- Skill instructions become the main orchestration mechanism.
- Migration agents edit shared files without ownership.
- Resume simply reruns the whole workflow.
- Workflow specs are untyped free-form prompt files.
