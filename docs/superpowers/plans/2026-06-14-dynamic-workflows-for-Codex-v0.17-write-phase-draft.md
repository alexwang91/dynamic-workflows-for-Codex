# Write Phase Draft Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist a reviewable write-phase draft artifact from validated structured write contracts.

**Architecture:** Add a focused `cdw.write_drafts` module that renders markdown from passed `BoundaryResult` records and registers it through the existing artifact index. Runtime calls the helper after boundary checks pass and before normal stage artifacts are written. This keeps write-draft behavior separate from generic artifact rendering and avoids real file writes.

**Tech Stack:** Python 3.10+, pydantic, pytest.

---

## File Structure

- Create `src/cdw/write_drafts.py`: render and persist `write phase draft` artifacts.
- Modify `src/cdw/runtime.py`: call write draft persistence after passed boundary checks.
- Modify `src/cdw/schemas.py`: no schema change expected unless tests expose a gap.
- Modify docs, skill, plugin metadata, generated plugin package, and version metadata.
- Add/modify tests in `tests/test_write_drafts.py`, `tests/test_runtime.py`, `tests/test_cli.py`, `tests/test_plugin_package.py`, and `tests/test_skill.py`.

## Task 1: Write Draft Helper

- [ ] **Step 1: Add failing helper tests**

Cover markdown rendering from structured path intents, idempotent artifact
record creation, and no draft for failed/missing structured contracts.

- [ ] **Step 2: Implement `src/cdw/write_drafts.py`**

Add `WRITE_PHASE_DRAFT_ARTIFACT_NAME`, `write_phase_draft_artifact`, and
markdown rendering helpers.

- [ ] **Step 3: Verify helper tests**

Run:

```powershell
python -m pytest tests/test_write_drafts.py -v
```

## Task 2: Runtime Integration

- [ ] **Step 1: Add failing runtime test**

Cover a strict guarded stage writing `write phase draft` after approval and
not duplicating it on resume.

- [ ] **Step 2: Integrate after passed boundary checks**

Call the write-draft helper only when the boundary result passes and includes
structured write path intents.

- [ ] **Step 3: Verify runtime tests**

Run:

```powershell
python -m pytest tests/test_runtime.py -v
```

## Task 3: CLI And Release Surface

- [ ] **Step 1: Add/update CLI and package tests**

Cover `cdw artifacts` listing the draft and metadata mentioning write phase
drafts.

- [ ] **Step 2: Update docs, skill, plugin, and versions**

Bump to `0.17.0`, document the draft artifact, and refresh the repo-local
plugin package with `python -m cdw bootstrap`.

- [ ] **Step 3: Verify related tests**

Run:

```powershell
python -m pytest tests/test_cli.py tests/test_plugin_package.py tests/test_skill.py -v
```

## Task 4: Full Verification And Push

- [ ] **Step 1: Run full test suite**

```powershell
python -m pytest -q
```

- [ ] **Step 2: Run readiness and package checks**

```powershell
python -m cdw doctor
python -m cdw live-smoke
@'
import json
from pathlib import Path
root = Path(".agents/plugins/plugins/dynamic-workflows-for-codex")
manifest = json.loads((root / ".codex-plugin" / "plugin.json").read_text())
assert manifest["name"] == "dynamic-workflows-for-codex"
assert manifest["version"] == "0.17.0"
assert manifest["skills"] == "./skills/"
assert len(manifest["interface"]["defaultPrompt"]) <= 3
assert (root / "skills" / "dynamic-workflows-for-codex" / "SKILL.md").exists()
'@ | python -
```

- [ ] **Step 3: Commit and push**

```powershell
git add .
git commit -m "feat: persist write phase drafts"
git push -u origin codex/write-phase-draft-v0.17
```
