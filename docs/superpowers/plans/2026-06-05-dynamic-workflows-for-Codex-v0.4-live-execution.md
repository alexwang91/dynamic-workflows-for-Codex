# dynamic-workflows-for-Codex v0.4 Live Execution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add configurable Codex command resolution for live smoke and live adapter execution.

**Architecture:** Introduce a focused resolver that centralizes CLI/env/PATH behavior. Thread the resolved command into `LiveCodexAdapter` and `run_live_smoke` instead of hardcoding `codex`.

**Tech Stack:** Python 3.10+, argparse, pytest.

---

## Task 1: Codex Command Resolver

**Files:**
- Create: `src/cdw/codex_command.py`
- Create: `tests/test_codex_command.py`

- [ ] **Step 1: Write failing tests**

```python
from cdw.codex_command import resolve_codex_command


def test_resolve_codex_command_prefers_explicit_value():
    resolution = resolve_codex_command(explicit="C:/tools/codex.exe", env={})

    assert resolution.command == "C:/tools/codex.exe"
    assert resolution.source == "cli"


def test_resolve_codex_command_uses_environment(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda command: None)
    resolution = resolve_codex_command(env={"CDW_CODEX_COMMAND": "D:/codex.exe"})

    assert resolution.command == "D:/codex.exe"
    assert resolution.source == "env"
```

- [ ] **Step 2: Run tests**

Run: `python -m pytest tests/test_codex_command.py -v`

Expected: FAIL because `cdw.codex_command` does not exist.

- [ ] **Step 3: Implement resolver**

Add:

- `CodexCommandResolution(command: str | None, source: Literal["cli", "env", "path", "missing"])`
- `resolve_codex_command(explicit: str | None = None, env: Mapping[str, str] | None = None)`

Use `CDW_CODEX_COMMAND` before `shutil.which("codex")`.

- [ ] **Step 4: Verify and commit**

Run:

```bash
python -m pytest tests/test_codex_command.py -v
git add src/cdw/codex_command.py tests/test_codex_command.py
git commit -m "feat: resolve codex command"
```

## Task 2: Use Resolved Command in Live Smoke

**Files:**
- Modify: `src/cdw/live_smoke.py`
- Modify: `src/cdw/cli.py`
- Modify: `tests/test_live_smoke.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write failing tests**

```python
def test_live_smoke_uses_explicit_codex_command(monkeypatch, tmp_path):
    calls = {}

    def fake_run(args, **kwargs):
        calls["args"] = args
        return subprocess.CompletedProcess(args, 0, stdout="codex-test 1.0", stderr="")

    monkeypatch.setattr("importlib.util.find_spec", lambda name: object())
    monkeypatch.setattr("subprocess.run", fake_run)

    report = run_live_smoke(tmp_path, codex_command="C:/tools/codex.exe")

    assert report.ok
    assert calls["args"][0] == "C:/tools/codex.exe"
    assert "cli" in report.to_text()
```

CLI:

```python
def test_live_smoke_command_accepts_codex_command(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr("importlib.util.find_spec", lambda name: object())
    monkeypatch.setattr(
        "subprocess.run",
        lambda args, **kwargs: subprocess.CompletedProcess(args, 0, stdout="ok", stderr=""),
    )

    exit_code = main(["live-smoke", "--root", str(tmp_path), "--codex-command", "codex-test"])

    assert exit_code == 0
    assert "codex-test" in capsys.readouterr().out
```

- [ ] **Step 2: Run tests**

Run: `python -m pytest tests/test_live_smoke.py tests/test_cli.py::test_live_smoke_command_accepts_codex_command -v`

Expected: FAIL because `run_live_smoke` and CLI lack `codex_command`.

- [ ] **Step 3: Implement live smoke wiring**

Add `codex_command` parameter to `run_live_smoke`.

Replace direct `shutil.which("codex")` with `resolve_codex_command()`.

Report source in the `codex-command` check message.

Add WindowsApps access-denied hint when the failed command path contains `WindowsApps`.

- [ ] **Step 4: Verify and commit**

Run:

```bash
python -m pytest tests/test_live_smoke.py tests/test_cli.py -v
git add src/cdw/live_smoke.py src/cdw/cli.py tests/test_live_smoke.py tests/test_cli.py
git commit -m "feat: configure live smoke codex command"
```

## Task 3: Use Resolved Command in Live Adapter

**Files:**
- Modify: `src/cdw/codex_mcp.py`
- Modify: `src/cdw/cli.py`
- Modify: `tests/test_codex_mcp.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write failing tests**

```python
def test_live_adapter_uses_configured_codex_command(monkeypatch, tmp_path):
    # Extend the existing fake MCP test:
    adapter = LiveCodexAdapter(root=tmp_path, codex_command="codex-test")
    result = adapter.run_worker(plan.work_units[0])
    assert calls["server_params"] == {"command": "codex-test", "args": ["mcp-server"]}
```

- [ ] **Step 2: Run tests**

Run: `python -m pytest tests/test_codex_mcp.py -v`

Expected: FAIL because `LiveCodexAdapter` has no `codex_command`.

- [ ] **Step 3: Implement adapter wiring**

Add `codex_command: str = "codex"` to `LiveCodexAdapter`.

Use it in `MCPServerStdio(params={"command": self.codex_command, "args": ["mcp-server"]})`.

Add `--codex-command` to live-capable CLI commands and pass it through `_build_adapter`.

- [ ] **Step 4: Verify and commit**

Run:

```bash
python -m pytest tests/test_codex_mcp.py tests/test_cli.py -v
git add src/cdw/codex_mcp.py src/cdw/cli.py tests/test_codex_mcp.py tests/test_cli.py
git commit -m "feat: configure live adapter codex command"
```

## Task 4: Docs and Final Verification

**Files:**
- Modify: `README.md`
- Modify: `docs/evaluation.md`

- [ ] **Step 1: Document command override**

Add examples:

```bash
CDW_CODEX_COMMAND=/path/to/codex python -m cdw live-smoke
python -m cdw live-smoke --codex-command /path/to/codex
python -m cdw review "Review this branch" --adapter live --codex-command /path/to/codex
```

- [ ] **Step 2: Verify**

Run:

```bash
python -m pytest -v
python -m cdw live-smoke
```

Expected: tests pass; local live smoke may fail due missing deps or Codex permissions, but it must report cleanly.

- [ ] **Step 3: Commit**

```bash
git add README.md docs/evaluation.md
git commit -m "docs: document live codex command override"
```
