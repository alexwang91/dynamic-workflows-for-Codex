# dynamic-workflows-for-Codex v0.5 Live Execute Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `cdw live-smoke --execute` use the same resolved Codex command it validated, return structured diagnostics when live execution fails, make the live Codex MCP request contract parseable in tests, expose that contract without requiring live dependencies, and add a Codex CLI adapter that uses the user's own logged-in Codex.

**Architecture:** Keep smoke diagnostics inside `src/cdw/live_smoke.py`. Keep live request shaping inside `src/cdw/codex_mcp.py` by adding a small contract builder that returns the Codex MCP tool name and arguments before rendering the coordinating-agent instruction. Add a CLI dry mode that prints that same contract as JSON before any live preflight checks run. Add `src/cdw/codex_cli.py` as a separate adapter that shells out to `codex exec`, preserving the existing runtime state/verification pipeline.

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

## Task 4: Make the Codex MCP Tool Contract Parseable

**Files:**
- Modify: `tests/test_codex_mcp.py`
- Modify: `src/cdw/codex_mcp.py`

- [ ] **Step 1: Write the failing test**

Add this test to `tests/test_codex_mcp.py`:

```python
import json
import re


def test_live_adapter_instruction_contains_parseable_codex_tool_contract(tmp_path):
    adapter = LiveCodexAdapter(
        root=tmp_path,
        sandbox="workspace-write",
        approval_policy="never",
    )

    instruction = adapter._codex_mcp_instruction("Inspect the current branch")
    match = re.search(r"```json\n(?P<json>.*?)\n```", instruction, re.DOTALL)

    assert match is not None
    assert json.loads(match.group("json")) == {
        "tool": "codex",
        "arguments": {
            "prompt": "Inspect the current branch",
            "cwd": str(tmp_path),
            "sandbox": "workspace-write",
            "approval-policy": "never",
        },
    }
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/test_codex_mcp.py::test_live_adapter_instruction_contains_parseable_codex_tool_contract -v`

Expected: FAIL because `_codex_mcp_instruction` currently emits prose bullets instead of a JSON contract block.

- [ ] **Step 3: Write minimal implementation**

Add `json` import and this helper to `LiveCodexAdapter`:

```python
def _codex_mcp_tool_contract(self, task_prompt: str) -> dict[str, object]:
    return {
        "tool": "codex",
        "arguments": {
            "prompt": task_prompt,
            "cwd": str(Path(self.root)),
            "sandbox": self.sandbox,
            "approval-policy": self.approval_policy,
        },
    }
```

Render it in `_codex_mcp_instruction` with a fenced JSON block.

- [ ] **Step 4: Run focused verification**

Run: `python -m pytest tests/test_codex_mcp.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add docs/superpowers/specs/2026-06-05-dynamic-workflows-for-Codex-v0.5-live-execute-contract.md docs/superpowers/plans/2026-06-05-dynamic-workflows-for-Codex-v0.5-live-execute-contract.md tests/test_codex_mcp.py src/cdw/codex_mcp.py
git commit -m "feat: add parseable codex mcp contract"
```

## Task 5: Expose the Live Smoke Contract Without Live Dependencies

**Files:**
- Modify: `tests/test_live_smoke.py`
- Modify: `tests/test_cli.py`
- Modify: `src/cdw/live_smoke.py`
- Modify: `src/cdw/cli.py`

- [ ] **Step 1: Write the failing core test**

Add this test to `tests/test_live_smoke.py`:

```python
from cdw.live_smoke import build_live_smoke_contract, run_live_smoke


def test_live_smoke_contract_does_not_run_preflight(monkeypatch, tmp_path):
    def fail_find_spec(name):
        raise AssertionError("dry contract must not check imports")

    def fail_run(args, **kwargs):
        raise AssertionError("dry contract must not execute subprocesses")

    monkeypatch.setattr("importlib.util.find_spec", fail_find_spec)
    monkeypatch.setattr("subprocess.run", fail_run)

    contract = build_live_smoke_contract(tmp_path)

    assert contract["tool"] == "codex"
    assert contract["arguments"]["cwd"] == str(tmp_path)
    assert contract["arguments"]["sandbox"] == "workspace-write"
    assert contract["arguments"]["approval-policy"] == "never"
    assert "live worker" in contract["arguments"]["prompt"]
```

- [ ] **Step 2: Run the core test to verify it fails**

Run: `python -m pytest tests/test_live_smoke.py::test_live_smoke_contract_does_not_run_preflight -v`

Expected: FAIL because `build_live_smoke_contract` does not exist.

- [ ] **Step 3: Write minimal core implementation**

Add `build_live_smoke_contract(root: Path) -> dict[str, object]` to
`src/cdw/live_smoke.py`. It should build `_live_smoke_plan()`, take the first
work unit, create `LiveCodexAdapter(root=root)`, and return the adapter's Codex
MCP tool contract for that work unit's worker prompt.

- [ ] **Step 4: Write the failing CLI test**

Add this test to `tests/test_cli.py`:

```python
def test_live_smoke_dry_contract_prints_json_without_preflight(
    tmp_path,
    capsys,
    monkeypatch,
):
    def fail_find_spec(name):
        raise AssertionError("dry contract must not check imports")

    def fail_run(args, **kwargs):
        raise AssertionError("dry contract must not execute subprocesses")

    monkeypatch.setattr("importlib.util.find_spec", fail_find_spec)
    monkeypatch.setattr("subprocess.run", fail_run)

    exit_code = main(["live-smoke", "--root", str(tmp_path), "--dry-contract"])

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert exit_code == 0
    assert data["tool"] == "codex"
    assert data["arguments"]["cwd"] == str(tmp_path)
```

- [ ] **Step 5: Run the CLI test to verify it fails**

Run: `python -m pytest tests/test_cli.py::test_live_smoke_dry_contract_prints_json_without_preflight -v`

Expected: FAIL because the parser does not accept `--dry-contract`.

- [ ] **Step 6: Write minimal CLI implementation**

Add `--dry-contract` to the `live-smoke` subcommand. In the `live-smoke` branch
of `main`, print:

```python
json.dumps(build_live_smoke_contract(Path(args.root)), indent=2)
```

and return `0` before calling `run_live_smoke`.

- [ ] **Step 7: Verify and commit**

Run:

```bash
python -m pytest tests/test_live_smoke.py tests/test_cli.py -v
python -m pytest -v
python -m cdw live-smoke --dry-contract
python -m cdw live-smoke
```

Expected: focused and full tests pass. `--dry-contract` exits zero with JSON.
Plain `live-smoke` may report local environment blockers but must not traceback.

Commit:

```bash
git add docs/superpowers/specs/2026-06-05-dynamic-workflows-for-Codex-v0.5-live-execute-contract.md docs/superpowers/plans/2026-06-05-dynamic-workflows-for-Codex-v0.5-live-execute-contract.md tests/test_live_smoke.py tests/test_cli.py src/cdw/live_smoke.py src/cdw/cli.py
git commit -m "feat: expose live smoke dry contract"
```

## Task 6: Add Codex CLI Adapter For User-Logged-In Codex

**Files:**
- Create: `src/cdw/codex_cli.py`
- Create: `tests/test_codex_cli.py`
- Modify: `src/cdw/cli.py`
- Modify: `tests/test_cli.py`
- Modify: `README.md`
- Modify: `docs/consumer-install.md`
- Modify: `docs/evaluation.md`

- [ ] **Step 1: Write failing adapter tests**

Create `tests/test_codex_cli.py`:

```python
import subprocess

import pytest

from cdw.codex_cli import CodexCliAdapter
from cdw.schemas import WorkerResult, WorkerStatus, WorkUnit


def test_codex_cli_adapter_runs_worker_with_codex_exec(monkeypatch, tmp_path):
    calls = {}

    def fake_run(args, **kwargs):
        calls["args"] = args
        calls["kwargs"] = kwargs
        return subprocess.CompletedProcess(args, 0, stdout="worker output", stderr="")

    monkeypatch.setattr("subprocess.run", fake_run)
    adapter = CodexCliAdapter(root=tmp_path, codex_command="codex-test")
    work_unit = WorkUnit(
        id="review",
        role="reviewer",
        goal="Review branch",
        prompt="Find issues",
        expected_output="Findings",
    )

    result = adapter.run_worker(work_unit)

    assert calls["args"][:-1] == [
        "codex-test",
        "exec",
        "-C",
        str(tmp_path),
        "-s",
        "workspace-write",
        "-a",
        "never",
    ]
    assert "Role: reviewer" in calls["args"][-1]
    assert calls["kwargs"]["encoding"] == "utf-8"
    assert result.status == "succeeded"
    assert result.raw_output == "worker output"


def test_codex_cli_adapter_verifies_first_line(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "subprocess.run",
        lambda args, **kwargs: subprocess.CompletedProcess(
            args,
            0,
            stdout="PASSED\nlooks good",
            stderr="",
        ),
    )
    adapter = CodexCliAdapter(root=tmp_path, codex_command="codex-test")
    worker_result = WorkerResult(
        work_unit_id="review",
        status=WorkerStatus.SUCCEEDED,
        summary="summary",
        evidence=["evidence"],
        raw_output="raw",
    )

    result = adapter.verify_worker_result(worker_result)

    assert result.status == "passed"
    assert "looks good" in result.notes


def test_codex_cli_adapter_raises_user_facing_error_on_cli_failure(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(
        "subprocess.run",
        lambda args, **kwargs: subprocess.CompletedProcess(
            args,
            1,
            stdout="",
            stderr="not logged in",
        ),
    )
    adapter = CodexCliAdapter(root=tmp_path, codex_command="codex-test")
    work_unit = WorkUnit(
        id="review",
        role="reviewer",
        goal="Review branch",
        prompt="Find issues",
        expected_output="Findings",
    )

    with pytest.raises(RuntimeError, match="not logged in"):
        adapter.run_worker(work_unit)
```

- [ ] **Step 2: Run adapter tests to verify they fail**

Run: `python -m pytest tests/test_codex_cli.py -v`

Expected: FAIL because `cdw.codex_cli` does not exist.

- [ ] **Step 3: Implement `CodexCliAdapter`**

Create `src/cdw/codex_cli.py` with a dataclass that:

- stores `root`, `sandbox`, `approval_policy`, `timeout_seconds`, and `codex_command`;
- runs `subprocess.run([codex_command, "exec", "-C", root, "-s", sandbox, "-a", approval_policy, prompt], capture_output=True, encoding="utf-8", errors="replace", timeout=timeout_seconds, check=False)`;
- returns `WorkerResult` for worker output;
- returns `VerificationResult` based on whether verifier output starts with `PASSED`;
- raises `RuntimeError` with the CLI output when `codex exec` fails.

- [ ] **Step 4: Wire CLI adapter**

Add `codex-cli` to every `--adapter` choice in `src/cdw/cli.py`.

Update `_build_adapter`:

```python
if config.adapter == "codex-cli":
    from cdw.codex_cli import CodexCliAdapter

    resolution = resolve_codex_command(explicit=codex_command)
    return CodexCliAdapter(
        root=config.root,
        codex_command=resolution.command or "codex",
    )
```

- [ ] **Step 5: Write CLI test**

Add to `tests/test_cli.py`:

```python
def test_codex_cli_adapter_runs_without_openai_agents(
    tmp_path,
    capsys,
    monkeypatch,
):
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "agents":
            raise ImportError("agents should not be imported")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    monkeypatch.setattr(
        "subprocess.run",
        lambda args, **kwargs: subprocess.CompletedProcess(
            args,
            0,
            stdout="PASSED\ncodex cli output",
            stderr="",
        ),
    )

    exit_code = main(
        [
            "plan",
            "Review branch",
            "--root",
            str(tmp_path),
            "--adapter",
            "codex-cli",
            "--codex-command",
            "codex-test",
        ]
    )

    assert exit_code == 0
    assert capsys.readouterr().out.startswith("run ")
```

- [ ] **Step 6: Run focused tests**

Run:

```bash
python -m pytest tests/test_codex_cli.py tests/test_cli.py::test_codex_cli_adapter_runs_without_openai_agents -v
```

Expected: PASS.

- [ ] **Step 7: Document and verify**

Add README and consumer docs examples:

```bash
codex login status
python -m cdw review "Review this branch" --adapter codex-cli
```

Run:

```bash
python -m pytest -v
python -m cdw live-smoke
```

Expected: tests pass; live-smoke preflight remains clean on this machine.

- [ ] **Step 8: Commit**

```bash
git add src/cdw/codex_cli.py tests/test_codex_cli.py src/cdw/cli.py tests/test_cli.py README.md docs/consumer-install.md docs/evaluation.md docs/superpowers/specs/2026-06-05-dynamic-workflows-for-Codex-v0.5-live-execute-contract.md docs/superpowers/plans/2026-06-05-dynamic-workflows-for-Codex-v0.5-live-execute-contract.md
git commit -m "feat: add codex cli adapter"
```
