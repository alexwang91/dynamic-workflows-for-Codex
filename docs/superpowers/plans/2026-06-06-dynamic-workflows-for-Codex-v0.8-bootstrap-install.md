# Dynamic Workflows For Codex v0.8 Bootstrap Install Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `cdw bootstrap` to prepare repo-local plugin files and print exact next install/verify commands for clone users.

**Architecture:** Add a small `cdw.bootstrap` module that reuses `package_repo_marketplace`. Wire a `bootstrap` subcommand in `cdw.cli`. Keep global Codex registration as a printed next step, not an automatic side effect.

**Tech Stack:** Python 3.10+, argparse, pytest, existing plugin packaging helpers.

---

## File Structure

- Create `src/cdw/bootstrap.py`: bootstrap report and file generation.
- Modify `src/cdw/cli.py`: add `bootstrap` command.
- Modify `tests/test_cli.py`: CLI behavior and output assertions.
- Create `tests/test_bootstrap.py`: direct bootstrap behavior.
- Modify `README.md`, `docs/consumer-install.md`, `docs/evaluation.md`, `CHANGELOG.md`, `pyproject.toml`, and plugin metadata for v0.8.

### Task 1: Failing Tests

**Files:**
- Create: `tests/test_bootstrap.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Add direct bootstrap test**

Assert `run_bootstrap(tmp_path)` writes marketplace and plugin manifest, returns
paths, and includes next-step commands.

- [ ] **Step 2: Add CLI bootstrap test**

Assert `main(["bootstrap", "--root", tmp_path])` returns 0 and prints
`marketplace`, `plugin`, `codex plugin marketplace add`, and `python -m cdw doctor`.

- [ ] **Step 3: Verify red**

```powershell
python -m pytest tests/test_bootstrap.py tests/test_cli.py::test_bootstrap_command_prepares_repo_plugin -v
```

Expected: import/subcommand failures because bootstrap does not exist.

### Task 2: Implementation

**Files:**
- Create: `src/cdw/bootstrap.py`
- Modify: `src/cdw/cli.py`

- [ ] **Step 1: Add report object**

Create `BootstrapReport` with `marketplace_path`, `plugin_path`, and `to_text()`.

- [ ] **Step 2: Add `run_bootstrap(root)`**

Call `package_repo_marketplace(root)`, derive plugin path, and return the report.

- [ ] **Step 3: Add CLI subcommand**

Wire `bootstrap --root .` to `run_bootstrap`.

- [ ] **Step 4: Run focused tests**

```powershell
python -m pytest tests/test_bootstrap.py tests/test_cli.py::test_bootstrap_command_prepares_repo_plugin -v
```

Expected: tests pass.

### Task 3: Docs And Version

**Files:**
- Modify: `README.md`
- Modify: `docs/consumer-install.md`
- Modify: `docs/evaluation.md`
- Modify: `CHANGELOG.md`
- Modify: `pyproject.toml`
- Modify: `src/cdw/plugin_package.py`
- Modify: `.agents/plugins/plugins/dynamic-workflows-for-codex/.codex-plugin/plugin.json`
- Modify: `tests/test_plugin_package.py`

- [ ] **Step 1: Bump to `0.8.0`**

- [ ] **Step 2: Add bootstrap to docs**

Put `python -m cdw bootstrap` before `python -m cdw doctor` in clone setup.

- [ ] **Step 3: Update evaluation checklist**

Add v0.8 bootstrap behavior.

### Task 4: Verification And Commit

- [ ] **Step 1: Run full tests**

```powershell
python -m pytest -v
```

- [ ] **Step 2: Run diagnostics**

```powershell
python -m cdw bootstrap
python -m cdw doctor
python -m cdw live-smoke
```

- [ ] **Step 3: Clean clone smoke**

Clone the current branch into a temp directory, create a venv, install
`.[dev]`, run tests, run bootstrap, and run doctor.

- [ ] **Step 4: Commit and push**

```powershell
git add ...
git commit -m "feat: add clone bootstrap command"
git push -u origin codex/bootstrap-install-v0.8
```
