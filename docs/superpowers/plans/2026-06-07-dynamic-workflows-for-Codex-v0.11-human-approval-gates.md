# Dynamic Workflows For Codex v0.11 Human Approval Gates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make manual and require-human workflow stages pause, persist, and resume only after explicit CLI approval.

**Architecture:** Extend run state with a pending approval marker and teach the staged runtime to stop before human-gated stages unless the currently pending stage is explicitly approved on resume. Keep the workflow spec schema unchanged and wire approval through the `resume` CLI command.

**Tech Stack:** Python 3.10+, pydantic, argparse, pytest.

---

## File Structure

- Modify `src/cdw/schemas.py`: add `waiting_for_human` synthesis status and `pending_human_approval`.
- Modify `src/cdw/runtime.py`: add `approve_human_gates` parameters and stage pause behavior.
- Modify `src/cdw/resume.py`: pass approval into resumed execution.
- Modify `src/cdw/cli.py`: add `resume --approve-human-gates` and waiting-for-human output.
- Modify `tests/test_runtime.py`, `tests/test_cli.py`, and `tests/test_resume.py`.
- Update release docs and plugin skill routing for v0.11.

## Task 1: Runtime Approval Tests

- [x] **Step 1: Add pause-before-manual-stage test**

Create a two-stage procedure where the second stage has `gate="manual_review"`.
Assert only first-stage workers run, `pending_human_approval` is the second
stage id, and synthesis status is `waiting_for_human`.

- [x] **Step 2: Add approved-resume test**

Load the paused state and resume with `approve_human_gates=True`. Assert second
stage workers run and synthesis completes.

- [x] **Step 3: Verify red**

Run:

```powershell
python -m pytest tests/test_runtime.py tests/test_resume.py -v
```

Expected: missing fields/parameters fail.

## Task 2: Runtime Implementation

- [x] **Step 1: Extend schemas**

Add `waiting_for_human` to synthesis status and
`pending_human_approval: str | None = None` to `RunState`.

- [x] **Step 2: Thread approval through runtime**

Add `approve_human_gates=False` to `execute_plan`,
`execute_workflow_bundle`, `execute_existing_state`, and
`ensure_procedure_results`.

- [x] **Step 3: Pause before human-gated stages**

If a stage has `manual_review` or `require_human` and approval is absent, set
`pending_human_approval`, save state, and stop before worker dispatch.

- [x] **Step 4: Clear pending approval when approved**

When approval is present on resume, clear only the matching pending stage before
executing it. Later human-gated stages must pause again.

## Task 3: CLI Approval Flag

- [x] **Step 1: Add `--approve-human-gates`**

Wire the flag to `resume`.

- [x] **Step 2: Add waiting output**

Make `_finish_run` print `waiting for human approval` and the stage id when the
synthesis status is `waiting_for_human`.

- [x] **Step 3: Add CLI tests**

Assert `cdw run` pauses on manual stage and `cdw resume --approve-human-gates`
completes.

## Task 4: Release Surface

- [x] **Step 1: Bump metadata to `0.11.0`**

Update package/plugin metadata and tests.

- [x] **Step 2: Update docs and skill routing**

Document `--approve-human-gates`, waiting state, and resume flow.

## Task 5: Verification And Commit

- [x] **Step 1: Run full tests**

```powershell
python -m pytest -v
```

- [x] **Step 2: Run readiness checks**

```powershell
python -m cdw doctor
python -m cdw live-smoke
python -m cdw bootstrap
python C:\Users\Administrator\.codex\skills\.system\plugin-creator\scripts\validate_plugin.py .agents\plugins\plugins\dynamic-workflows-for-codex
```

- [x] **Step 3: Commit and push**

```powershell
git add .
git commit -m "feat: add human approval gates"
git push -u origin codex/human-approval-gates-v0.11
```
