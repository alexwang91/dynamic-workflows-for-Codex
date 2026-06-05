# dynamic-workflows-for-Codex v0.5 Live Execute Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `cdw live-smoke --execute` use the same resolved Codex command it validated and return structured diagnostics when live execution fails.

**Architecture:** Keep the change inside `src/cdw/live_smoke.py`. Treat `LiveCodexAdapter` as the execution boundary and improve only how `run_live_smoke` constructs it and records execution results.

**Tech Stack:** Python 3.10+, pytest.

---

## Task 1: Prove Execute Uses the Resolved Codex Command

**Files:**
- Modify: `tests/test_live_smoke.py`
- Modify: `src/cdw/live_smoke.py`

- [ ] **Step 1: Write the failing test**

Add this test to `tests/test_live_smoke.py`:

```python
from types import SimpleNamespace


def test_live_smoke_execute_uses_resolved_codex_command(monkeypatch, tmp_path):
    captured = {}

    monkeypatch.setattr("importlib.util.find_spec", lambda name: object())
    monkeypatch.setattr(
        "subprocess.run",
        lambda args, **kwargs: subprocess.CompletedProcess(
            args,
            0,
            stdout="codex-test 1.0",
            stderr="",
        ),
    )
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    def fake_execute_plan(plan, root, adapter):
        captured["codex_command"] = adapter.codex_command
        return SimpleNamespace(run_id="live123")

    monkeypatch.setattr("cdw.live_smoke.execute_plan", fake_execute_plan)

    report = run_live_smoke(tmp_path, execute=True, codex_command="codex-test")

    assert report.ok
    assert report.run_id == "live123"
    assert captured["codex_command"] == "codex-test"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/test_live_smoke.py::test_live_smoke_execute_uses_resolved_codex_command -v`

Expected: FAIL because `LiveCodexAdapter` is still created without the resolved command.

- [ ] **Step 3: Write minimal implementation**

Change `run_live_smoke` so the execute path constructs:

```python
LiveCodexAdapter(root=root, codex_command=resolution.command or "codex")
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `python -m pytest tests/test_live_smoke.py::test_live_smoke_execute_uses_resolved_codex_command -v`

Expected: PASS.

## Task 2: Report Live Execution Failures Without Tracebacks

**Files:**
- Modify: `tests/test_live_smoke.py`
- Modify: `src/cdw/live_smoke.py`

- [ ] **Step 1: Write the failing test**

Add this test to `tests/test_live_smoke.py`:

```python
def test_live_smoke_execute_reports_runtime_failure(monkeypatch, tmp_path):
    monkeypatch.setattr("importlib.util.find_spec", lambda name: object())
    monkeypatch.setattr(
        "subprocess.run",
        lambda args, **kwargs: subprocess.CompletedProcess(
            args,
            0,
            stdout="codex-test 1.0",
            stderr="",
        ),
    )
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    def fake_execute_plan(plan, root, adapter):
        raise RuntimeError("live failed")

    monkeypatch.setattr("cdw.live_smoke.execute_plan", fake_execute_plan)

    report = run_live_smoke(tmp_path, execute=True, codex_command="codex-test")

    assert not report.ok
    assert any(check.name == "live-run" and not check.ok for check in report.checks)
    assert "live failed" in report.to_text()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/test_live_smoke.py::test_live_smoke_execute_reports_runtime_failure -v`

Expected: FAIL because the exception escapes instead of becoming a report check.

- [ ] **Step 3: Write minimal implementation**

Wrap the execute call:

```python
try:
    state = execute_plan(
        _live_smoke_plan(),
        root,
        LiveCodexAdapter(root=root, codex_command=resolution.command or "codex"),
    )
except Exception as exc:
    report.checks.append(CheckResult(name="live-run", ok=False, message=str(exc)))
else:
    report.checks.append(
        CheckResult(name="live-run", ok=True, message="live worker completed.")
    )
    report.run_id = state.run_id
```

- [ ] **Step 4: Run the focused tests**

Run: `python -m pytest tests/test_live_smoke.py -v`

Expected: PASS.

## Task 3: Verify and Commit

**Files:**
- Modify: `docs/superpowers/specs/2026-06-05-dynamic-workflows-for-Codex-v0.5-live-execute-contract.md`
- Modify: `docs/superpowers/plans/2026-06-05-dynamic-workflows-for-Codex-v0.5-live-execute-contract.md`
- Modify: `tests/test_live_smoke.py`
- Modify: `src/cdw/live_smoke.py`

- [ ] **Step 1: Run full verification**

Run:

```bash
python -m pytest -v
python -m cdw live-smoke
```

Expected: tests pass. Local live smoke may report missing dependencies or Codex
CLI access blockers, but it must return a clean report without a Python
traceback.

- [ ] **Step 2: Commit**

```bash
git add docs/superpowers/specs/2026-06-05-dynamic-workflows-for-Codex-v0.5-live-execute-contract.md docs/superpowers/plans/2026-06-05-dynamic-workflows-for-Codex-v0.5-live-execute-contract.md tests/test_live_smoke.py src/cdw/live_smoke.py
git commit -m "fix: harden live smoke execute contract"
```

