# Artifact Registry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist declared stage artifacts and hydrate dependent stage prompts with consumed artifact content.

**Architecture:** Add a small artifact module that owns artifact paths, safe file names, writes, reads, and lookup. Keep runtime orchestration in `runtime.py`: after a stage passes its gate, write artifacts; before stage workers run, hydrate work unit prompts with consumed artifacts. Extend run status and CLI formatting without changing the workflow spec schema.

**Tech Stack:** Python 3.10+, pydantic, argparse, pytest.

---

## File Structure

- Create `src/cdw/artifacts.py`: artifact pathing, write/read/list helpers, prompt context formatting.
- Modify `src/cdw/schemas.py`: add `ArtifactRecord` and `RunState.artifacts`.
- Modify `src/cdw/runtime.py`: write produced artifacts after passing stage gates and hydrate consumed artifacts before worker execution.
- Modify `src/cdw/run_status.py`: include artifact summaries in run summaries.
- Modify `src/cdw/cli.py`: add `artifacts` and `artifact` commands plus status output.
- Modify tests in `tests/test_runtime.py`, `tests/test_cli.py`, `tests/test_run_status.py`, and add `tests/test_artifacts.py`.
- Update release docs, skill routing, plugin metadata, generated repo-local plugin package, and version metadata.

## Task 1: Artifact Model And Helpers

- [x] **Step 1: Add failing artifact helper tests**

Cover slugging names, writing markdown artifacts, reading artifacts by name,
and ambiguity when more than one stage produces the same name.

- [x] **Step 2: Implement `ArtifactRecord` and `src/cdw/artifacts.py`**

Add an artifact record model and helper functions for writing stage artifacts,
reading consumed artifacts, and formatting context for prompts.

## Task 2: Runtime Artifact Flow

- [x] **Step 1: Add runtime tests**

Assert a passed producing stage writes artifact files, a failed producing stage
does not, and a consuming stage receives upstream artifact content in its prompt.

- [x] **Step 2: Implement runtime integration**

Call artifact write helpers after stage gates pass and hydrate work unit prompts
before adapter execution.

## Task 3: CLI Artifact Inspection

- [x] **Step 1: Add CLI/status tests**

Assert `status --json` includes artifacts, text status prints artifact paths,
`cdw artifacts <run-id>` lists artifacts, and `cdw artifact <run-id> <name>`
prints artifact content.

- [x] **Step 2: Implement CLI/status output**

Extend `RunSummary`, `status`, `artifacts`, and `artifact` commands with
user-facing errors and JSON output where appropriate.

## Task 4: Release Surface

- [x] **Step 1: Bump metadata to `0.14.0`**

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
python -m pytest tests/test_artifacts.py tests/test_runtime.py tests/test_cli.py tests/test_run_status.py -v
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
git commit -m "feat: persist workflow artifacts"
git push -u origin codex/artifact-registry-v0.14
```
