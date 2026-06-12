# Workflow Spec Expression Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add stage dependencies, artifact flow, and stricter write-heavy migration boundaries to v3 workflow specs.

**Architecture:** Extend `WorkflowStage` with dependency, artifact, and stage write-policy fields while preserving defaults for older specs. Validate the richer procedure graph in `WorkflowSpecBundle`, then make the existing sequential runtime stop before blocked dependent stages.

**Tech Stack:** Python 3.10+, pydantic, argparse, pytest.

---

## File Structure

- Modify `src/cdw/schemas.py`: add `StageWritePolicy`, new `WorkflowStage` fields, and richer procedure validation.
- Modify `src/cdw/runtime.py`: stop dependent stages until prerequisite gates pass.
- Modify `src/cdw/workflow_spec.py`: emit v0.13 fields for generated specs, especially migrations.
- Modify `src/cdw/dynamic_planner.py`: include new fields in fake dynamic specs, prompt, and JSON output schema.
- Modify `tests/test_workflow_spec.py`, `tests/test_runtime.py`, `tests/test_dynamic_planner.py`, and `tests/test_migrate.py`.
- Update release docs, skill routing, plugin metadata, generated repo-local plugin package, and version metadata.

## Task 1: Schema Tests

- [x] **Step 1: Add dependency validation tests**

Add tests that reject:

- unknown stage dependency ids,
- a stage depending on itself,
- a stage depending on a later stage.

Run:

```powershell
python -m pytest tests/test_workflow_spec.py::test_workflow_spec_rejects_unknown_stage_dependency tests/test_workflow_spec.py::test_workflow_spec_rejects_self_stage_dependency tests/test_workflow_spec.py::test_workflow_spec_rejects_out_of_order_stage_dependency -v
```

- [x] **Step 2: Add artifact validation test**

Assert a stage with `consumes=["migration inventory"]` fails unless the consumed
artifact is produced by one of its declared dependencies.

- [x] **Step 3: Add write policy validation tests**

Assert `guarded` or `write-heavy` stages require `manual_review` or
`require_human`, and top-level `write-heavy` specs require human approval.

## Task 2: Schema Implementation

- [x] **Step 1: Extend `WorkflowStage`**

Add:

```python
StageWritePolicy = Literal["read-only", "guarded", "write-heavy"]
depends_on: list[str] = Field(default_factory=list)
consumes: list[str] = Field(default_factory=list)
produces: list[str] = Field(default_factory=list)
write_policy: StageWritePolicy = "read-only"
```

- [x] **Step 2: Validate stage graph**

In `WorkflowSpecBundle.validate_procedure_references`, validate unique stage
ids, known earlier dependencies, artifact consumption through declared
dependencies, guarded/write-heavy stage gates, and top-level write-heavy human
approval.

## Task 3: Runtime Dependency Execution

- [x] **Step 1: Add runtime dependency test**

Create a two-stage procedure where stage two depends on stage one. Make stage
one verification fail. Assert stage two workers do not run.

- [x] **Step 2: Add dependency gate check**

Before executing a stage, if any `depends_on` stage has not passed its gate,
break out of procedure execution.

## Task 4: Generated Specs And Dynamic Planner

- [x] **Step 1: Update migration spec generation**

`migration-inventory` should produce `migration inventory`.
`migration-plan-review` should depend on `migration-inventory`, consume
`migration inventory`, produce `guarded patch plan` and `migration risk review`,
and use `write_policy="guarded"`.

- [x] **Step 2: Update fake dynamic planner**

Add artifact and dependency fields to fake dynamic stages.

- [x] **Step 3: Update Codex CLI planner contract**

Add new stage fields to `_workflow_spec_output_schema()` and mention them in
`_dynamic_planner_prompt()`.

## Task 5: Release Surface

- [x] **Step 1: Bump metadata to `0.13.0`**

Update package and plugin versions, README badges, changelog, evaluation docs,
consumer docs, skill text, and plugin metadata.

- [x] **Step 2: Refresh repo-local plugin package**

Run:

```powershell
python -m cdw bootstrap
```

## Task 6: Verification And Push

- [x] **Step 1: Run targeted tests**

```powershell
python -m pytest tests/test_workflow_spec.py tests/test_runtime.py tests/test_dynamic_planner.py tests/test_migrate.py -v
```

- [x] **Step 2: Run full verification**

```powershell
python -m pytest -v
python -m cdw doctor
python -m cdw live-smoke
python C:\Users\Administrator\.codex\skills\.system\plugin-creator\scripts\validate_plugin.py .agents\plugins\plugins\dynamic-workflows-for-codex
```

- [x] **Step 3: Commit and push**

```powershell
git add .
git commit -m "feat: strengthen workflow spec stages"
git push -u origin codex/workflow-spec-expression-v0.13
```
