# Dynamic Workflows For Codex v0.9 Codex CLI Smoke Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development for the adapter fix and superpowers:verification-before-completion before declaring the branch ready.

**Goal:** Fix the current Codex CLI adapter argument contract and verify the real clone-user `codex-cli` path.

**Architecture:** Keep `cdw.codex_cli.CodexCliAdapter` as the adapter boundary. Change only the command argument list, leaving worker prompt construction, verifier behavior, and runtime orchestration intact.

**Tech Stack:** Python 3.10+, argparse, pytest, local Codex CLI.

---

## File Structure

- Modify `tests/test_codex_cli.py`: regression assertion for current args.
- Modify `src/cdw/codex_cli.py`: remove unsupported approval-policy CLI arg
  and strip Windows process-cleanup noise from Codex CLI output.
- Modify `tests/test_cli.py` and `src/cdw/cli.py`: return non-zero for
  incomplete workflow synthesis.
- Modify `README.md`, `CHANGELOG.md`, `docs/evaluation.md`, `pyproject.toml`, plugin metadata, and packaging tests for v0.9.

## Task 1: Failing Regression Test

- [ ] **Step 1: Update expected adapter args**

Expect:

```python
["codex-test", "exec", "-C", str(tmp_path), "-s", "workspace-write"]
```

- [ ] **Step 2: Guard against old flag**

Assert `"-a" not in calls["args"]`.

- [ ] **Step 3: Verify red**

```powershell
python -m pytest tests/test_codex_cli.py::test_codex_cli_adapter_runs_worker_with_codex_exec -v
```

Expected: failure showing the old implementation still passes `-a`.

## Task 2: Minimal Adapter Fix

- [ ] **Step 1: Remove old CLI args**

Remove `"-a", self.approval_policy` from `_run_codex`.

- [ ] **Step 2: Verify focused green**

```powershell
python -m pytest tests/test_codex_cli.py -v
```

Expected: all Codex CLI adapter tests pass.

## Task 3: Output Cleanup And CLI Exit

- [ ] **Step 1: Add Codex CLI output noise tests**

Simulate Windows process-cleanup lines before worker output and verifier
verdicts.

- [ ] **Step 2: Strip cleanup noise in the adapter**

Remove only `SUCCESS: The process with PID ... has been terminated.` lines.

- [ ] **Step 3: Add CLI incomplete exit test**

Use a failing verifier adapter and assert the CLI returns 1 while still printing
the run id.

- [ ] **Step 4: Add CLI run finalizer**

Print `run <id>` for every run and return 1 when synthesis is incomplete.

## Task 4: Release Surface

- [ ] **Step 1: Bump metadata to `0.9.0`**

Update Python package metadata, plugin manifest generation, repo-local plugin
manifest, and tests.

- [ ] **Step 2: Update docs**

Add v0.9 notes to README, CHANGELOG, and evaluation checklist.

## Task 5: Verification And Publish

- [ ] **Step 1: Run full deterministic tests**

```powershell
python -m pytest -v
```

- [ ] **Step 2: Run local readiness checks**

```powershell
python -m cdw doctor
python -m cdw live-smoke
python -m cdw bootstrap
```

- [ ] **Step 3: Run real minimal codex-cli smoke**

Create a temp git repo, save a minimal workflow spec, and run it with:

```powershell
python -m cdw run <spec> --root <temp-repo> --adapter codex-cli
```

Expected: command uses the user's logged-in Codex CLI. When quota is available,
the temp repo shows only expected smoke artifacts and synthesis completes; when
quota is exhausted, the command fails clearly without traceback.

- [ ] **Step 4: Commit and push**

```powershell
git add ...
git commit -m "fix: support current codex exec args"
git push -u origin codex/codex-cli-smoke-v0.9
```
