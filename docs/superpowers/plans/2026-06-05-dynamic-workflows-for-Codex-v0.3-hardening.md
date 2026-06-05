# dynamic-workflows-for-Codex v0.3 Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add live-mode smoke diagnostics, v2 workflow spec envelopes, and a repo-local Codex plugin package command.

**Architecture:** Keep runtime orchestration in Python. Add focused modules for live smoke checks, spec envelope parsing, and plugin package writing. Preserve v1 spec compatibility by keeping `load_workflow_spec()` returning a `WorkflowPlan`.

**Tech Stack:** Python 3.10+, Pydantic v2, argparse, pytest, Codex plugin manifest JSON.

---

## File Structure

- Create `src/cdw/live_smoke.py`: live dependency and Codex CLI diagnostics.
- Modify `src/cdw/cli.py`: add `live-smoke` and `package-plugin`, route v2 specs.
- Modify `src/cdw/schemas.py`: add workflow spec envelope models.
- Modify `src/cdw/workflow_spec.py`: save v2 envelopes and load v1/v2.
- Create `src/cdw/plugin_package.py`: write plugin manifest and packaged skill.
- Modify `src/cdw/skill.py`: share skill body generation with installer/package code.
- Create `tests/test_live_smoke.py`: preflight checks and CLI failure reporting.
- Modify `tests/test_workflow_spec.py`: v2 envelope and v1 compatibility coverage.
- Create `tests/test_plugin_package.py`: plugin package shape coverage.
- Modify `tests/test_cli.py`: CLI coverage for new commands.
- Modify `README.md` and `docs/evaluation.md`: document v0.3 hardening commands.

## Task 1: Live Smoke Diagnostics

**Files:**
- Create: `src/cdw/live_smoke.py`
- Modify: `src/cdw/cli.py`
- Create: `tests/test_live_smoke.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write failing tests**

```python
from cdw.live_smoke import run_live_smoke


def test_live_smoke_reports_missing_codex_without_traceback(monkeypatch, tmp_path):
    monkeypatch.setattr("shutil.which", lambda command: None)

    report = run_live_smoke(tmp_path, execute=False)

    assert not report.ok
    assert any(check.name == "codex-command" and not check.ok for check in report.checks)
    assert "not found" in report.to_text().lower()
```

Add CLI coverage:

```python
def test_live_smoke_command_reports_failure(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr("shutil.which", lambda command: None)

    exit_code = main(["live-smoke", "--root", str(tmp_path)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "codex-command" in captured.out
```

- [ ] **Step 2: Run tests**

Run: `python -m pytest tests/test_live_smoke.py tests/test_cli.py::test_live_smoke_command_reports_failure -v`

Expected: FAIL because `cdw.live_smoke` and CLI command do not exist.

- [ ] **Step 3: Implement live smoke**

Implement `CheckResult`, `LiveSmokeReport`, and `run_live_smoke(root, execute=False)`.

Checks:

- `importlib.util.find_spec("agents")`
- `importlib.util.find_spec("openai")`
- `shutil.which("codex")`
- `subprocess.run([codex_path, "--version"], ...)`, catching `OSError`, `PermissionError`, and timeout.
- `OPENAI_API_KEY` only required when `execute=True`.

If `execute=True` and checks pass, run a one-unit `WorkflowPlan` through `LiveCodexAdapter`.

- [ ] **Step 4: Wire CLI**

Add:

```bash
cdw live-smoke --root . [--execute]
```

Print `report.to_text()` and return `0` when `report.ok`, otherwise `1`.

- [ ] **Step 5: Verify and commit**

Run:

```bash
python -m pytest tests/test_live_smoke.py tests/test_cli.py -v
git add src/cdw/live_smoke.py src/cdw/cli.py tests/test_live_smoke.py tests/test_cli.py
git commit -m "feat: add live smoke diagnostics"
```

## Task 2: v2 Workflow Spec Envelope

**Files:**
- Modify: `src/cdw/schemas.py`
- Modify: `src/cdw/workflow_spec.py`
- Modify: `tests/test_workflow_spec.py`

- [ ] **Step 1: Write failing tests**

```python
from cdw.planner import build_plan
from cdw.workflow_spec import load_workflow_spec, load_workflow_spec_bundle, save_workflow_spec


def test_workflow_spec_saves_v2_envelope(tmp_path):
    plan = build_plan("migrate", "Rename User model to Account")
    path = tmp_path / "migrate.workflow.json"

    save_workflow_spec(path, plan)
    bundle = load_workflow_spec_bundle(path)

    assert bundle.schema_version == "2"
    assert bundle.kind == "codex.dynamic-workflow"
    assert bundle.plan == plan
    assert bundle.constraints.write_policy == "write-heavy"
    assert bundle.constraints.requires_human_approval is True


def test_load_workflow_spec_accepts_v1_plan_root(tmp_path):
    plan = build_plan("review", "Review branch")
    path = tmp_path / "review-v1.workflow.json"
    path.write_text(plan.model_dump_json(indent=2), encoding="utf-8")

    loaded = load_workflow_spec(path)

    assert loaded == plan
```

- [ ] **Step 2: Run tests**

Run: `python -m pytest tests/test_workflow_spec.py -v`

Expected: FAIL because bundle models and loader do not exist.

- [ ] **Step 3: Implement schema models**

Add:

- `WorkflowSpecMetadata`
- `WorkflowSpecConstraints`
- `WorkflowSpecBundle`

Use `Literal["2"]` for bundle `schema_version` and `Literal["codex.dynamic-workflow"]` for `kind`.

- [ ] **Step 4: Implement save/load compatibility**

`save_workflow_spec(path, plan)` writes a v2 bundle.

`load_workflow_spec_bundle(path)` returns a bundle for v2 files and wraps v1 plan-root files.

`load_workflow_spec(path)` returns `bundle.plan`.

- [ ] **Step 5: Verify and commit**

Run:

```bash
python -m pytest tests/test_workflow_spec.py tests/test_cli.py -v
git add src/cdw/schemas.py src/cdw/workflow_spec.py tests/test_workflow_spec.py
git commit -m "feat: add v2 workflow spec envelope"
```

## Task 3: Plugin Package Command

**Files:**
- Create: `src/cdw/plugin_package.py`
- Modify: `src/cdw/skill.py`
- Modify: `src/cdw/cli.py`
- Create: `tests/test_plugin_package.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write failing tests**

```python
import json

from cdw.plugin_package import package_plugin


def test_package_plugin_writes_manifest_and_skill(tmp_path):
    path = package_plugin(tmp_path)

    manifest_path = path / ".codex-plugin" / "plugin.json"
    skill_path = path / "skills" / "dynamic-workflows-for-codex" / "SKILL.md"

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    content = skill_path.read_text(encoding="utf-8")

    assert path == tmp_path / "dynamic-workflows-for-codex"
    assert manifest["name"] == "dynamic-workflows-for-codex"
    assert manifest["skills"] == "./skills/"
    assert "runtime owns orchestration" in content
```

Add CLI coverage:

```python
def test_package_plugin_command_writes_package(tmp_path, capsys):
    exit_code = main(["package-plugin", "--output", str(tmp_path)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out.strip().startswith("plugin ")
    assert (tmp_path / "dynamic-workflows-for-codex" / ".codex-plugin" / "plugin.json").exists()
```

- [ ] **Step 2: Run tests**

Run: `python -m pytest tests/test_plugin_package.py tests/test_cli.py::test_package_plugin_command_writes_package -v`

Expected: FAIL because `cdw.plugin_package` and CLI command do not exist.

- [ ] **Step 3: Implement plugin package writer**

Write:

- `.codex-plugin/plugin.json`
- `skills/dynamic-workflows-for-codex/SKILL.md`

Keep plugin name lowercase. Reuse shared skill body generation with a configurable skill name.

- [ ] **Step 4: Verify with plugin validator**

Run:

```bash
python -m pytest tests/test_plugin_package.py tests/test_cli.py -v
python C:/Users/Administrator/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py .cdw/plugin-smoke/dynamic-workflows-for-codex
```

- [ ] **Step 5: Commit**

```bash
git add src/cdw/plugin_package.py src/cdw/skill.py src/cdw/cli.py tests/test_plugin_package.py tests/test_cli.py
git commit -m "feat: package codex plugin"
```

## Task 4: Docs and Smoke

**Files:**
- Modify: `README.md`
- Modify: `docs/evaluation.md`

- [ ] **Step 1: Document v0.3 commands**

Add examples for:

```bash
cdw live-smoke
cdw live-smoke --execute
cdw package-plugin --output plugins
```

- [ ] **Step 2: Full verification**

Run:

```bash
python -m pytest -v
python -m cdw live-smoke
python -m cdw plan "Review this branch" --save-spec .cdw/specs/review-v2.workflow.json
python -m cdw run .cdw/specs/review-v2.workflow.json --adapter fake
python -m cdw package-plugin --output .cdw/plugin-smoke
python C:/Users/Administrator/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py .cdw/plugin-smoke/dynamic-workflows-for-codex
```

- [ ] **Step 3: Commit**

```bash
git add README.md docs/evaluation.md
git commit -m "docs: document v0.3 hardening"
```
