# Structured Write Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a machine-readable write contract for guarded/write-heavy workflow stages.

**Architecture:** Extend boundary parsing with a structured `WRITE_CONTRACT` JSON section while keeping legacy `WRITE_PATHS` support. Store parsed contract state in `BoundaryResult`, require contracts through `WorkflowSpecConstraints.requires_write_contract`, and inject contract instructions into guarded/write-heavy worker prompts when needed.

**Tech Stack:** Python 3.10+, pydantic, argparse, json, pytest.

---

## File Structure

- Modify `src/cdw/schemas.py`: add `WritePathIntent`, `requires_write_contract`, and boundary contract fields.
- Modify `src/cdw/boundaries.py`: parse structured `WRITE_CONTRACT` JSON and enforce missing-contract failures.
- Modify `src/cdw/runtime.py`: append write-contract instructions to strict guarded/write-heavy stage prompts.
- Modify `src/cdw/planner.py`: require structured contracts in migration patch-plan output.
- Modify `src/cdw/workflow_spec.py`: set migration `requires_write_contract=True` and produce `write path contract`.
- Modify `src/cdw/dynamic_planner.py`: expose the new constraint field to model-generated specs.
- Modify docs, plugin metadata, generated plugin package, and version metadata.
- Add/modify tests in `tests/test_boundaries.py`, `tests/test_runtime.py`, `tests/test_migrate.py`, `tests/test_workflow_spec.py`, `tests/test_dynamic_planner.py`, `tests/test_plugin_package.py`, and `tests/test_skill.py`.

## Task 1: Structured Boundary Parsing

- [x] **Step 1: Add failing parser tests**

Cover `WRITE_CONTRACT` JSON object extraction, path intent defaults, invalid
absolute/parent paths, and required-contract missing failure.

- [x] **Step 2: Implement schema and parser support**

Add `WritePathIntent`, parse structured contracts, and expose parsed intent data
on `BoundaryResult`.

- [x] **Step 3: Verify parser tests**

Run:

```powershell
python -m pytest tests/test_boundaries.py -v
```

## Task 2: Runtime Prompt And Boundary Enforcement

- [x] **Step 1: Add failing runtime tests**

Cover required contract prompt injection and missing-contract failure before
artifact writing.

- [x] **Step 2: Implement runtime prompt injection**

Append a concise `WRITE_CONTRACT` instruction only for guarded/write-heavy
stages when `requires_write_contract=True`.

- [x] **Step 3: Verify runtime tests**

Run:

```powershell
python -m pytest tests/test_runtime.py -v
```

## Task 3: Migration Spec Contract Defaults

- [x] **Step 1: Add failing migration/spec tests**

Cover generated migration `requires_write_contract=True`, patch-plan prompt
requirements, and `write path contract` artifact production.

- [x] **Step 2: Update planner/spec generation**

Set the migration constraint flag, update migration prompts, and add the new
artifact name to migration plan-review outputs.

- [x] **Step 3: Verify migration/spec tests**

Run:

```powershell
python -m pytest tests/test_migrate.py tests/test_workflow_spec.py -v
```

## Task 4: Dynamic Planner, Release Surface, And Package

- [x] **Step 1: Add failing dynamic planner and package tests**

Cover the new schema field, skill language, plugin metadata, and version bump.

- [x] **Step 2: Update dynamic planner, docs, skill, plugin, and versions**

Bump to `0.16.0`, document structured write contracts, and refresh the
repo-local plugin package with `python -m cdw bootstrap`.

- [x] **Step 3: Verify related tests**

Run:

```powershell
python -m pytest tests/test_dynamic_planner.py tests/test_plugin_package.py tests/test_skill.py -v
```

## Task 5: Full Verification And Push

- [x] **Step 1: Run full test suite**

```powershell
python -m pytest -q
```

- [x] **Step 2: Run readiness and package checks**

```powershell
python -m cdw doctor
python -m cdw live-smoke
@'
import json
from pathlib import Path
root = Path(".agents/plugins/plugins/dynamic-workflows-for-codex")
manifest = json.loads((root / ".codex-plugin" / "plugin.json").read_text())
assert manifest["name"] == "dynamic-workflows-for-codex"
assert manifest["version"] == "0.16.0"
assert manifest["skills"] == "./skills/"
assert len(manifest["interface"]["defaultPrompt"]) <= 3
assert (root / "skills" / "dynamic-workflows-for-codex" / "SKILL.md").exists()
'@ | python -
```

- [x] **Step 3: Commit and push**

```powershell
git add .
git commit -m "feat: require structured write contracts"
git push -u origin codex/structured-write-contract-v0.16
```
