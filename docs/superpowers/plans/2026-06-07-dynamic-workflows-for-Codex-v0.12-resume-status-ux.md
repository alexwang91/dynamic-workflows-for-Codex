# Resume Status UX Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add read-only CLI commands that show persisted run status, pending human approval stages, and resume commands.

**Architecture:** Keep run state as the source of truth and add a small inspection module that reads `.cdw/runs/<run-id>/state.json`. The CLI formats the same summary data as human text or JSON without executing workers or modifying state.

**Tech Stack:** Python 3.10+, pathlib, argparse, pydantic, pytest.

---

## File Structure

- Create `src/cdw/run_status.py` for run summary loading, listing, and formatting data.
- Modify `src/cdw/schemas.py`, `src/cdw/state.py`, and `src/cdw/runtime.py` to persist the adapter name for adapter-aware resume hints.
- Modify `src/cdw/cli.py` to add `status` and `runs` subcommands.
- Modify `tests/test_cli.py` for CLI behavior coverage.
- Add `tests/test_run_status.py` for inspection module behavior.
- Update `README.md`, `CHANGELOG.md`, `docs/consumer-install.md`, `docs/evaluation.md`, `src/cdw/skill.py`, `src/cdw/plugin_package.py`, and generated repo-local plugin files for v0.12.

## Task 1: CLI Status Tests

- [x] **Step 1: Add paused status CLI test**

Add a test that runs a manual-gated spec, captures the run id, then calls:

```powershell
python -m pytest tests/test_cli.py::test_status_reports_waiting_human_run -v
```

Expected initial result before implementation: parser rejects `status`.

- [x] **Step 2: Add status JSON CLI test**

Assert `cdw status <run-id> --json` returns parseable JSON with
`status="waiting_for_human"`, `pending_human_approval="manual-review"`, and a
resume command containing `--approve-human-gates`.

- [x] **Step 3: Add missing run CLI test**

Assert `cdw status missing --root <tmp>` exits non-zero and prints
`error: run not found: missing`.

## Task 2: Run Inspection Module

- [x] **Step 1: Add module tests**

Create `tests/test_run_status.py` with tests for:

- summarizing a loaded run state,
- listing runs newest first by `state.json` mtime,
- returning an empty list when `.cdw/runs` does not exist.

- [x] **Step 2: Implement `RunSummary`**

Create a dataclass with:

```python
run_id: str
status: str
command: str
request: str
adapter: str | None
pending_human_approval: str | None
worker_count: int
verification_count: int
state_path: str
resume_command: str | None
```

- [x] **Step 3: Implement loading helpers**

Add:

```python
summarize_run(root: Path, run_id: str) -> RunSummary
list_run_summaries(root: Path) -> list[RunSummary]
```

`summarize_run` raises `RuntimeError("run not found: <run-id>")` when the
state file is absent. `list_run_summaries` skips unreadable/corrupt state files.
When `pending_human_approval` and `adapter` are present, `resume_command`
includes `--adapter <adapter>`.

## Task 3: CLI Wiring

- [x] **Step 1: Add parser commands**

Add:

```text
cdw status <run-id> --root <repo> --json
cdw runs --root <repo> --json
```

- [x] **Step 2: Add human text format**

Status output should include line-oriented fields:

```text
run <id>
status <status>
command <command>
request <request>
adapter <adapter>
pending <stage-id>
resume python -m cdw resume <id> --adapter <adapter> --approve-human-gates
state <path>
```

`pending` and `resume` are omitted when not waiting for human approval.

- [x] **Step 3: Add JSON format**

Use `json.dumps(..., indent=2)` for `status --json` and `runs --json`.

## Task 4: Release Surface

- [x] **Step 1: Bump metadata to `0.12.0`**

Update package and plugin version values from `0.11.0` to `0.12.0`.

- [x] **Step 2: Update docs and skill routing**

Document `cdw status`, `cdw runs`, JSON output, and the approval-oriented
resume hint.

- [x] **Step 3: Refresh repo-local plugin package**

Run:

```powershell
python -m cdw bootstrap
```

## Task 5: Verification And Push

- [x] **Step 1: Run targeted tests**

```powershell
python -m pytest tests/test_run_status.py tests/test_cli.py -v
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
git commit -m "feat: add run status commands"
git push -u origin codex/resume-status-ux-v0.12
```
