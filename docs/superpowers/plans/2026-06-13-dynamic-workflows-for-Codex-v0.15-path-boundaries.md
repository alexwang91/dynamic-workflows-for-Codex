# Path Boundaries Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enforce declared write path boundaries for guarded/write-heavy workflow stages.

**Architecture:** Add a focused boundary module for path extraction, normalization, pattern matching, and boundary result creation. Store workflow constraints and boundary results in `RunState`, run boundary checks after worker verification but before artifact writing, then expose failures through status output. CLI path overrides update workflow spec constraints before saving or running.

**Tech Stack:** Python 3.10+, pydantic, argparse, fnmatch, pytest.

---

## File Structure

- Create `src/cdw/boundaries.py`: path extraction, matching, and boundary checks.
- Modify `src/cdw/schemas.py`: add `BoundaryViolation`, `BoundaryResult`, `RunState.constraints`, and `RunState.boundary_results`.
- Modify `src/cdw/state.py`: persist constraints in new run states.
- Modify `src/cdw/runtime.py`: run boundary checks for guarded/write-heavy stages.
- Modify `src/cdw/cli.py`: add `--allow-path` / `--forbid-path` and show boundary failures.
- Modify `src/cdw/run_status.py`: include boundary summaries.
- Modify `src/cdw/workflow_spec.py`: add default migration forbidden paths.
- Add/modify tests in `tests/test_boundaries.py`, `tests/test_runtime.py`, `tests/test_cli.py`, `tests/test_run_status.py`, and `tests/test_workflow_spec.py`.
- Update release docs, skill routing, plugin metadata, generated repo-local plugin package, and version metadata.

## Task 1: Boundary Module

- [x] **Step 1: Add boundary extraction and matching tests**

Cover explicit `WRITE_PATHS:` sections, allowed path matches, forbidden path
precedence, absolute paths, and parent traversal.

- [x] **Step 2: Implement `src/cdw/boundaries.py`**

Implement extraction, path normalization, pattern matching, and stage boundary
check result construction.

## Task 2: Runtime Boundary Results

- [x] **Step 1: Add runtime boundary tests**

Cover passing guarded stage boundary checks after approval, failed boundary
checks causing incomplete synthesis, and failed checks preventing artifact
creation.

- [x] **Step 2: Integrate boundary checks into runtime**

Persist constraints in run state, record boundary results after verification,
and stop before artifacts/later stages on boundary failure.

## Task 3: CLI And Status

- [x] **Step 1: Add CLI/status tests**

Cover parser flags, saved spec overrides, direct run overrides, text status, and
JSON status boundary failures.

- [x] **Step 2: Implement CLI/status support**

Apply constraint overrides to saved and direct workflow bundles, and expose
boundary failures in run summaries.

## Task 4: Release Surface

- [x] **Step 1: Bump metadata to `0.15.0`**

Update package and plugin versions, README badges, changelog, evaluation docs,
consumer docs, skill text, and plugin metadata.

- [x] **Step 2: Refresh repo-local plugin package**

Run:

```powershell
python -m cdw bootstrap
```

## Task 5: Verification And Push

- [x] **Step 1: Run targeted tests**

```powershell
python -m pytest tests/test_boundaries.py tests/test_runtime.py tests/test_cli.py tests/test_run_status.py tests/test_workflow_spec.py -v
```

- [x] **Step 2: Run full verification**

```powershell
python -m pytest -v
python -m cdw doctor
python -m cdw live-smoke
@'
import json
from pathlib import Path
root = Path(".agents/plugins/plugins/dynamic-workflows-for-codex")
manifest = json.loads((root / ".codex-plugin" / "plugin.json").read_text())
assert manifest["name"] == "dynamic-workflows-for-codex"
assert manifest["version"] == "0.15.0"
assert manifest["skills"] == "./skills/"
assert len(manifest["interface"]["defaultPrompt"]) <= 3
assert (root / "skills" / "dynamic-workflows-for-codex" / "SKILL.md").exists()
'@ | python -
```

- [x] **Step 3: Commit and push**

```powershell
git add .
git commit -m "feat: enforce path boundaries"
git push -u origin codex/path-boundaries-v0.15
```
