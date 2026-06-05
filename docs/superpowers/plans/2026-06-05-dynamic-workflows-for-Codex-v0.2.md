# dynamic-workflows-for-Codex v0.2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add resumable runs, workflow specs, a repo-local Codex skill wrapper, and a guarded first migration workflow.

**Architecture:** Extend the existing typed runtime instead of moving orchestration into prompts. Workflow specs are JSON files validated by `WorkflowPlan`; resume reuses persisted `RunState`; migration remains guarded and does not auto-merge edits; the Codex skill only invokes `cdw`.

**Tech Stack:** Python 3.10+, Pydantic v2, argparse, pytest.

---

## Task 1: Workflow Spec Files

**Files:**
- Create: `src/cdw/workflow_spec.py`
- Create: `tests/test_workflow_spec.py`
- Modify: `src/cdw/schemas.py`

- [ ] **Step 1: Write failing round-trip test**

```python
from cdw.planner import build_plan
from cdw.workflow_spec import load_workflow_spec, save_workflow_spec


def test_workflow_spec_round_trip(tmp_path):
    plan = build_plan("review", "Review branch")
    path = tmp_path / "review.workflow.json"

    save_workflow_spec(path, plan)
    loaded = load_workflow_spec(path)

    assert loaded == plan
    assert loaded.schema_version == "1"
```

- [ ] **Step 2: Run test**

Run: `python -m pytest tests/test_workflow_spec.py -v`

Expected: FAIL because `cdw.workflow_spec` does not exist.

- [ ] **Step 3: Implement `schema_version` and spec helpers**

Add `schema_version: str = "1"` to `WorkflowPlan`.

Create `src/cdw/workflow_spec.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

from cdw.schemas import WorkflowPlan


def save_workflow_spec(path: Path, plan: WorkflowPlan) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(plan.model_dump_json(indent=2), encoding="utf-8")
    return path


def load_workflow_spec(path: Path) -> WorkflowPlan:
    data = json.loads(path.read_text(encoding="utf-8"))
    return WorkflowPlan.model_validate(data)
```

- [ ] **Step 4: Verify**

Run: `python -m pytest tests/test_workflow_spec.py tests/test_schemas.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/cdw/workflow_spec.py src/cdw/schemas.py tests/test_workflow_spec.py
git commit -m "feat: add workflow spec files"
```

## Task 2: CLI Plan Save and Run Spec

**Files:**
- Modify: `src/cdw/cli.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write failing CLI tests**

```python
def test_plan_can_save_workflow_spec(tmp_path):
    spec_path = tmp_path / "review.workflow.json"

    exit_code = main(["plan", "Review branch", "--save-spec", str(spec_path)])

    assert exit_code == 0
    assert spec_path.exists()


def test_run_executes_workflow_spec(tmp_path, capsys):
    spec_path = tmp_path / "review.workflow.json"
    main(["plan", "Review branch", "--save-spec", str(spec_path)])

    exit_code = main(["run", str(spec_path), "--root", str(tmp_path), "--adapter", "fake"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out.strip().startswith("run ")
```

- [ ] **Step 2: Run tests**

Run: `python -m pytest tests/test_cli.py::test_plan_can_save_workflow_spec tests/test_cli.py::test_run_executes_workflow_spec -v`

Expected: FAIL because CLI lacks `--save-spec` and `run`.

- [ ] **Step 3: Implement CLI changes**

- Add `--save-spec` to `plan`.
- If `--save-spec` is provided, save the plan and print `spec <path>` without executing.
- Add `run <workflow_spec>` command that loads the spec and executes it.

- [ ] **Step 4: Verify**

Run: `python -m pytest tests/test_cli.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/cdw/cli.py tests/test_cli.py
git commit -m "feat: run saved workflow specs"
```

## Task 3: Resumable Runtime

**Files:**
- Create: `src/cdw/resume.py`
- Modify: `src/cdw/runtime.py`
- Modify: `src/cdw/state.py`
- Create: `tests/test_resume.py`

- [ ] **Step 1: Write failing resume test**

```python
from cdw.codex_mcp import FakeCodexAdapter
from cdw.planner import build_plan
from cdw.resume import resume_run
from cdw.runtime import execute_plan
from cdw.state import load_run_state, save_run_state


def test_resume_fills_missing_verifier_without_rerunning_workers(tmp_path):
    plan = build_plan("review", "Review branch")
    state = execute_plan(plan, tmp_path, FakeCodexAdapter())
    state.verification_results = state.verification_results[:2]
    state.synthesis = None
    save_run_state(tmp_path, state)

    resumed = resume_run(tmp_path, state.run_id, FakeCodexAdapter())

    loaded = load_run_state(tmp_path, state.run_id)
    assert resumed.run_id == state.run_id
    assert len(resumed.worker_results) == len(plan.work_units)
    assert len(resumed.verification_results) == len(plan.work_units)
    assert loaded.synthesis is not None
```

- [ ] **Step 2: Run test**

Run: `python -m pytest tests/test_resume.py -v`

Expected: FAIL because `cdw.resume` does not exist.

- [ ] **Step 3: Implement idempotent phases**

- Extract runtime helpers:
  - `ensure_worker_results(state, adapter)`
  - `ensure_verification_results(state, adapter)`
  - `finalize_synthesis(state)`
- Implement `resume_run(root, run_id, adapter)` by loading state and calling missing phases.

- [ ] **Step 4: Verify**

Run: `python -m pytest tests/test_resume.py tests/test_runtime.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/cdw/resume.py src/cdw/runtime.py src/cdw/state.py tests/test_resume.py
git commit -m "feat: resume incomplete workflow runs"
```

## Task 4: CLI Resume

**Files:**
- Modify: `src/cdw/cli.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write failing CLI resume test**

```python
def test_resume_command_continues_existing_run(tmp_path, capsys):
    main(["review", "Review branch", "--root", str(tmp_path), "--adapter", "fake"])
    run_id = capsys.readouterr().out.strip().split()[-1]

    exit_code = main(["resume", run_id, "--root", str(tmp_path), "--adapter", "fake"])

    assert exit_code == 0
    assert f"run {run_id}" in capsys.readouterr().out
```

- [ ] **Step 2: Run test**

Run: `python -m pytest tests/test_cli.py::test_resume_command_continues_existing_run -v`

Expected: FAIL because CLI lacks `resume`.

- [ ] **Step 3: Implement CLI resume**

Add `resume <run_id>` with `--root` and `--adapter`.

- [ ] **Step 4: Verify**

Run: `python -m pytest tests/test_cli.py tests/test_resume.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/cdw/cli.py tests/test_cli.py
git commit -m "feat: add resume command"
```

## Task 5: Guarded Migration Workflow

**Files:**
- Modify: `src/cdw/schemas.py`
- Modify: `src/cdw/planner.py`
- Modify: `src/cdw/cli.py`
- Create: `tests/test_migrate.py`

- [ ] **Step 1: Write failing migration planner test**

```python
from cdw.planner import build_plan


def test_migration_plan_is_guarded_and_write_heavy():
    plan = build_plan("migrate", "Rename User model to Account")

    assert plan.command == "migrate"
    assert plan.pattern == "guarded-migration"
    assert plan.verification_strategy == "patch-review"
    assert all("ownership" in unit.prompt.lower() for unit in plan.work_units)
```

- [ ] **Step 2: Run test**

Run: `python -m pytest tests/test_migrate.py -v`

Expected: FAIL because `migrate` is unsupported.

- [ ] **Step 3: Implement migration plan**

- Add `MIGRATE = "migrate"` to `Command`.
- Add `_migration_plan()` in `planner.py`.
- Add `migrate` command to CLI.
- Keep fake-mode execution only; live prompts must include ownership/safety constraints.

- [ ] **Step 4: Verify**

Run: `python -m pytest tests/test_migrate.py tests/test_planner.py tests/test_cli.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/cdw/schemas.py src/cdw/planner.py src/cdw/cli.py tests/test_migrate.py
git commit -m "feat: add guarded migration workflow"
```

## Task 6: Repo-Local Codex Skill Installer

**Files:**
- Create: `src/cdw/skill.py`
- Modify: `src/cdw/cli.py`
- Create: `tests/test_skill.py`

- [ ] **Step 1: Write failing skill installer test**

```python
from cdw.skill import install_skill


def test_install_skill_writes_repo_skill(tmp_path):
    path = install_skill(tmp_path)

    assert path == tmp_path / ".agents" / "skills" / "dynamic-workflows-for-Codex" / "SKILL.md"
    content = path.read_text(encoding="utf-8")
    assert "name: dynamic-workflows-for-Codex" in content
    assert "cdw" in content
    assert "runtime owns orchestration" in content
```

- [ ] **Step 2: Run test**

Run: `python -m pytest tests/test_skill.py -v`

Expected: FAIL because `cdw.skill` does not exist.

- [ ] **Step 3: Implement skill installer**

Create `install_skill(root: Path) -> Path` that writes `.agents/skills/dynamic-workflows-for-Codex/SKILL.md`.

- [ ] **Step 4: Add CLI command**

Add `cdw install-skill --root <path>`.

- [ ] **Step 5: Verify**

Run: `python -m pytest tests/test_skill.py tests/test_cli.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/cdw/skill.py src/cdw/cli.py tests/test_skill.py
git commit -m "feat: install codex skill wrapper"
```

## Task 7: Docs and Final Verification

**Files:**
- Modify: `README.md`
- Modify: `docs/evaluation.md`

- [ ] **Step 1: Document v0.2 commands**

Add examples for:

```bash
cdw plan "Review this branch" --save-spec review.workflow.json
cdw run review.workflow.json --adapter fake
cdw resume <run-id> --adapter fake
cdw migrate "Rename User model to Account" --adapter fake
cdw install-skill
```

- [ ] **Step 2: Verify full suite**

Run: `python -m pytest -v`

Expected: all tests pass.

- [ ] **Step 3: Run smoke checks**

Run:

```powershell
python -m cdw plan "Review this branch" --save-spec .cdw/specs/review.workflow.json
python -m cdw run .cdw/specs/review.workflow.json --adapter fake
python -m cdw migrate "Rename User model to Account" --adapter fake
python -m cdw install-skill
```

Expected: all commands exit 0 and create expected artifacts.

- [ ] **Step 4: Commit**

```bash
git add README.md docs/evaluation.md
git commit -m "docs: document v0.2 workflows"
```
