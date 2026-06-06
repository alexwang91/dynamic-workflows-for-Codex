# Dynamic Workflows For Codex v0.6 Runtime Procedure Execution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `cdw run <workflow-spec>` execute v3 procedure graph stages, gates, and failure behavior.

**Architecture:** Add a procedure-aware runtime entrypoint that accepts `WorkflowSpecBundle`, persists the selected procedure in `RunState`, and executes workers stage by stage. Keep `execute_plan` backward compatible by wrapping a plan in the generated default bundle.

**Tech Stack:** Python 3.10+, Pydantic v2, pytest, existing runtime state model and fake adapter.

---

## File Structure

- Modify `src/cdw/schemas.py`: add optional `procedure` to `RunState`.
- Modify `src/cdw/state.py`: let `create_run_state` accept an optional procedure.
- Modify `src/cdw/runtime.py`: add `execute_workflow_bundle`, staged execution helpers, and an existing-state execution helper for resume.
- Modify `src/cdw/resume.py`: resume staged runs through stored procedure.
- Modify `src/cdw/cli.py`: make `run` load `WorkflowSpecBundle` and call `execute_workflow_bundle`.
- Modify `tests/test_runtime.py`: staged `stop`, `continue`, persistence, and resume behavior.
- Modify `README.md`, `CHANGELOG.md`, and `docs/evaluation.md`: describe procedure-aware runtime behavior.

### Task 1: Failing Runtime Tests

**Files:**
- Modify: `tests/test_runtime.py`

- [ ] **Step 1: Add `execute_workflow_bundle` tests**

Create a two-stage bundle. Stage one fails with `on_failure="stop"` and stage
two should not run. Then create the same shape with `on_failure="continue"` and
stage two should run.

- [ ] **Step 2: Add persistence test**

Assert the returned and saved `RunState` both contain the procedure.

- [ ] **Step 3: Add resume test**

After a stopped staged run, call `resume_run` and assert later-stage workers are
still not run.

- [ ] **Step 4: Verify red**

```powershell
python -m pytest tests/test_runtime.py tests/test_resume.py -v
```

Expected: import or attribute failures because `execute_workflow_bundle` and
`RunState.procedure` do not exist yet.

### Task 2: Schema And State

**Files:**
- Modify `src/cdw/schemas.py`
- Modify `src/cdw/state.py`

- [ ] **Step 1: Add procedure to `RunState`**

Add `procedure: WorkflowProcedure | None = None`.

- [ ] **Step 2: Extend `create_run_state`**

Accept `procedure: WorkflowProcedure | None = None` and pass it into
`RunState`.

- [ ] **Step 3: Run state tests**

```powershell
python -m pytest tests/test_state.py tests/test_runtime.py -v
```

Expected: state compatibility remains intact; runtime tests may still fail
until Task 3.

### Task 3: Runtime Execution

**Files:**
- Modify `src/cdw/runtime.py`

- [ ] **Step 1: Add `execute_workflow_bundle`**

Create state with `bundle.plan` and `bundle.procedure`, save it, execute
existing state, and return it.

- [ ] **Step 2: Keep `execute_plan` compatible**

Wrap the plan with `build_workflow_spec_bundle(plan)` and call
`execute_workflow_bundle`.

- [ ] **Step 3: Add staged helpers**

Add helpers for stage worker execution, stage verification execution, and stage
gate evaluation.

- [ ] **Step 4: Run runtime tests**

```powershell
python -m pytest tests/test_runtime.py -v
```

Expected: staged stop/continue/persistence tests pass.

### Task 4: CLI And Resume

**Files:**
- Modify `src/cdw/cli.py`
- Modify `src/cdw/resume.py`

- [ ] **Step 1: CLI run path**

Load `load_workflow_spec_bundle` for `run` and call `execute_workflow_bundle`.

- [ ] **Step 2: Resume path**

Replace the flat ensure/finalize calls with `execute_existing_state`, which uses
`state.procedure` when present.

- [ ] **Step 3: Run CLI/resume tests**

```powershell
python -m pytest tests/test_cli.py tests/test_resume.py -v
```

Expected: existing CLI and resume tests pass.

### Task 5: Documentation, Verification, Commit

**Files:**
- Modify `README.md`
- Modify `CHANGELOG.md`
- Modify `docs/evaluation.md`

- [ ] **Step 1: Update docs**

Describe v0.6 as procedure-aware: saved specs include procedure graphs and
runtime uses those graphs for `cdw run`.

- [ ] **Step 2: Run verification**

```powershell
python -m pytest -v
python -m cdw doctor
python -m cdw live-smoke
```

Expected: all tests and diagnostics pass.

- [ ] **Step 3: Commit and push**

```powershell
git add docs/superpowers/specs/2026-06-06-dynamic-workflows-for-Codex-v0.6-runtime-procedure-execution.md docs/superpowers/plans/2026-06-06-dynamic-workflows-for-Codex-v0.6-runtime-procedure-execution.md src/cdw/schemas.py src/cdw/state.py src/cdw/runtime.py src/cdw/resume.py src/cdw/cli.py tests/test_runtime.py tests/test_resume.py README.md CHANGELOG.md docs/evaluation.md
git commit -m "feat: execute workflow procedure stages"
git push
```
