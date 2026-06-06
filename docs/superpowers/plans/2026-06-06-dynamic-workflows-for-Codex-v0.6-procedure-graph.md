# Dynamic Workflows For Codex v0.6 Procedure Graph Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a v3 workflow procedure graph that describes stages, gates, triggers, and failure behavior while preserving v1/v2 compatibility.

**Architecture:** Extend `cdw.schemas` with procedure graph models and validation. Extend `cdw.workflow_spec` to generate default procedures for saved specs and for legacy v2 bundles that do not include one. Runtime continues to execute `WorkflowPlan` unchanged in this slice.

**Tech Stack:** Python 3.10+, Pydantic v2, pytest, existing JSON workflow spec serializer.

---

## File Structure

- Modify `src/cdw/schemas.py`: add `WorkflowStage`, `WorkflowProcedure`, procedure enums, and bundle validation.
- Modify `src/cdw/workflow_spec.py`: save v3 bundles and fill default procedures for v1/v2 compatibility.
- Modify `tests/test_workflow_spec.py`: add v3 save/load, v2 compatibility, and invalid reference tests.
- Modify `tests/test_schemas.py`: add direct procedure validation tests if needed.
- Modify `README.md` and `docs/evaluation.md`: document v3 procedure graph.
- Add spec and plan docs under `docs/superpowers`.

### Task 1: Failing Workflow Spec Tests

**Files:**
- Modify: `tests/test_workflow_spec.py`

- [ ] **Step 1: Add v3 save test**

```python
def test_workflow_spec_saves_v3_procedure_graph(tmp_path):
    plan = build_plan("review", "Review branch")
    path = tmp_path / "review.workflow.json"

    save_workflow_spec(path, plan)
    bundle = load_workflow_spec_bundle(path)

    assert bundle.schema_version == "3"
    assert bundle.procedure is not None
    assert bundle.procedure.mode == "fan-out"
    assert bundle.procedure.stages[0].work_unit_ids == [
        work_unit.id for work_unit in plan.work_units
    ]
    assert bundle.procedure.stages[0].gate == "all_required_verified"
```

- [ ] **Step 2: Add v2 compatibility test**

Create a v2 JSON envelope without `procedure`, load it, and assert the loader
fills a default procedure while preserving the plan.

- [ ] **Step 3: Add invalid reference test**

Create a v3 envelope where one stage references `missing-worker`. Assert
`load_workflow_spec_bundle` raises a `pydantic.ValidationError`.

- [ ] **Step 4: Verify red**

Run:

```powershell
python -m pytest tests/test_workflow_spec.py -v
```

Expected: tests fail because procedure graph fields do not exist and saved
specs still use schema version `2`.

### Task 2: Schema Models And Validation

**Files:**
- Modify: `src/cdw/schemas.py`

- [ ] **Step 1: Add literals and models**

Add:

```python
StageGate = Literal["all_required_verified", "any_verified", "manual_review"]
FailureBehavior = Literal["stop", "continue", "require_human"]
ProcedureMode = Literal["single-stage", "fan-out", "sequence", "guarded"]
```

Add `WorkflowStage` and `WorkflowProcedure` Pydantic models with `extra="forbid"`.

- [ ] **Step 2: Extend `WorkflowSpecBundle`**

Allow `schema_version` to be `"2"` or `"3"`, default to `"3"`, and add
`procedure: WorkflowProcedure | None = None`.

- [ ] **Step 3: Validate procedure references**

Use a model validator on `WorkflowSpecBundle` to ensure every referenced work
unit id exists, no work unit id is duplicated across stages, and all plan work
units are covered when `procedure` is present.

- [ ] **Step 4: Run schema/spec tests**

```powershell
python -m pytest tests/test_workflow_spec.py tests/test_schemas.py -v
```

Expected: procedure reference validation behaves correctly; default generation
may still fail until Task 3 is complete.

### Task 3: Procedure Defaults And Backward Compatibility

**Files:**
- Modify: `src/cdw/workflow_spec.py`

- [ ] **Step 1: Update `_bundle_for_plan`**

Saved specs should use `schema_version="3"` and include
`procedure=_procedure_for_plan(plan)`.

- [ ] **Step 2: Add `_procedure_for_plan`**

Generate plan-specific procedure defaults:

- `review`: `fan-out`, one stage covering all workers.
- `debug`: `fan-out`, one stage covering all investigators.
- `plan`: `single-stage`, one planner stage.
- `migrate`: `guarded`, inventory stage first, patch planning and verification
  second.

- [ ] **Step 3: Fill missing procedure after v2 load**

In `load_workflow_spec_bundle`, validate the incoming bundle, and when
`bundle.procedure is None`, return `bundle.model_copy(update={"procedure": _procedure_for_plan(bundle.plan)})`.

- [ ] **Step 4: Run workflow spec tests**

```powershell
python -m pytest tests/test_workflow_spec.py -v
```

Expected: all workflow spec tests pass.

### Task 4: Documentation

**Files:**
- Modify: `README.md`
- Modify: `docs/evaluation.md`

- [ ] **Step 1: Update README**

State that saved specs are v3 envelopes with metadata, constraints,
acceptance criteria, procedure graph, and embedded plan.

- [ ] **Step 2: Update evaluation checklist**

Add v0.6 behavior for v3 procedure graph, v2 compatibility, and validation.

### Task 5: Verification And Commit

**Files:**
- All changed files

- [ ] **Step 1: Run focused tests**

```powershell
python -m pytest tests/test_workflow_spec.py tests/test_schemas.py -v
```

Expected: all selected tests pass.

- [ ] **Step 2: Run full tests**

```powershell
python -m pytest -v
```

Expected: full suite passes.

- [ ] **Step 3: Run local diagnostics**

```powershell
python -m cdw doctor
python -m cdw live-smoke
```

Expected: diagnostic reports print without traceback.

- [ ] **Step 4: Commit**

```powershell
git add docs/superpowers/specs/2026-06-06-dynamic-workflows-for-Codex-v0.6-procedure-graph.md docs/superpowers/plans/2026-06-06-dynamic-workflows-for-Codex-v0.6-procedure-graph.md src/cdw/schemas.py src/cdw/workflow_spec.py tests/test_workflow_spec.py tests/test_schemas.py README.md docs/evaluation.md
git commit -m "feat: add workflow procedure graph"
```
