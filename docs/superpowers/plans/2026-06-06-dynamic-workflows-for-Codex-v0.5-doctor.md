# Dynamic Workflows For Codex v0.5 Doctor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `cdw doctor`, a clone-user readiness diagnostic for local runtime, plugin packaging, and the user's own Codex CLI.

**Architecture:** A new `cdw.doctor` module owns diagnostic checks and returns a parseable report object. The CLI delegates to that module and exits `0` only when all checks pass. Documentation treats `doctor` as the first consumer setup command before fake, codex-cli, or live workflows.

**Tech Stack:** Python 3.10+, argparse, dataclasses, pytest, existing `cdw.codex_command` resolver.

---

## File Structure

- Create `src/cdw/doctor.py`: diagnostic report types and check functions.
- Create `tests/test_doctor.py`: unit tests for successful diagnostics, missing Codex CLI, plugin checks, and non-executing behavior.
- Modify `src/cdw/cli.py`: add the `doctor` command and route to `run_doctor`.
- Modify `tests/test_cli.py`: assert the CLI exposes and prints doctor results.
- Modify `README.md`, `docs/consumer-install.md`, `docs/evaluation.md`, and `src/cdw/skill.py`: document the clone-user diagnostic path.
- Regenerate or update `.agents/plugins/plugins/dynamic-workflows-for-codex/skills/dynamic-workflows-for-codex/SKILL.md` and plugin metadata if packaging text changes.

### Task 1: Doctor Unit Tests

**Files:**
- Create: `tests/test_doctor.py`

- [ ] **Step 1: Write the failing tests**

```python
import subprocess

from cdw.doctor import run_doctor


def _write_plugin_package(root):
    skill_path = (
        root
        / ".agents"
        / "plugins"
        / "plugins"
        / "dynamic-workflows-for-codex"
        / "skills"
        / "dynamic-workflows-for-codex"
        / "SKILL.md"
    )
    manifest_path = skill_path.parents[2] / ".codex-plugin" / "plugin.json"
    marketplace_path = root / ".agents" / "plugins" / "marketplace.json"
    skill_path.parent.mkdir(parents=True)
    manifest_path.parent.mkdir(parents=True)
    marketplace_path.parent.mkdir(parents=True, exist_ok=True)
    skill_path.write_text("# skill", encoding="utf-8")
    manifest_path.write_text("{}", encoding="utf-8")
    marketplace_path.write_text("{}", encoding="utf-8")


def test_doctor_reports_ready_clone(monkeypatch, tmp_path):
    _write_plugin_package(tmp_path)
    calls = []

    def fake_run(args, **kwargs):
        calls.append(args)
        if args[1] == "--version":
            return subprocess.CompletedProcess(args, 0, stdout="codex-cli 1.0", stderr="")
        if args[1:] == ["login", "status"]:
            return subprocess.CompletedProcess(args, 0, stdout="logged in", stderr="")
        return subprocess.CompletedProcess(args, 0, stdout="exec help", stderr="")

    monkeypatch.setattr("subprocess.run", fake_run)

    report = run_doctor(tmp_path, codex_command="codex-test")

    assert report.ok
    assert [check.name for check in report.checks] == [
        "cdw-runtime",
        "cdw-state",
        "codex-command",
        "codex-version",
        "codex-login",
        "codex-exec",
        "plugin-package",
        "skill-package",
    ]
    assert calls == [
        ["codex-test", "--version"],
        ["codex-test", "login", "status"],
        ["codex-test", "exec", "--help"],
    ]


def test_doctor_reports_missing_codex_without_running_subprocess(monkeypatch, tmp_path):
    monkeypatch.setattr("shutil.which", lambda command: None)

    def fail_run(args, **kwargs):
        raise AssertionError("doctor should not run subprocess without codex")

    monkeypatch.setattr("subprocess.run", fail_run)

    report = run_doctor(tmp_path)

    assert not report.ok
    assert any(check.name == "codex-command" and not check.ok for check in report.checks)
    assert "not found" in report.to_text().lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
python -m pytest tests/test_doctor.py -v
```

Expected: import failure for `cdw.doctor`.

### Task 2: Doctor Implementation

**Files:**
- Create: `src/cdw/doctor.py`

- [ ] **Step 1: Implement report and checks**

```python
from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from cdw.codex_command import CodexCommandResolution, resolve_codex_command


@dataclass
class CheckResult:
    name: str
    ok: bool
    message: str


@dataclass
class DoctorReport:
    checks: list[CheckResult] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(check.ok for check in self.checks)

    def to_text(self) -> str:
        lines = []
        for check in self.checks:
            status = "ok" if check.ok else "failed"
            lines.append(f"{check.name}: {status} - {check.message}")
        return "\n".join(lines)
```

- [ ] **Step 2: Add `run_doctor` and helpers**

Use `resolve_codex_command`, create and remove a `.cdw/.doctor-write-test`
probe file, run `codex --version`, `codex login status`, and
`codex exec --help`, then check the repo-local plugin and skill paths.

- [ ] **Step 3: Run tests**

Run:

```powershell
python -m pytest tests/test_doctor.py -v
```

Expected: all doctor tests pass.

### Task 3: CLI Wiring

**Files:**
- Modify: `src/cdw/cli.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Add CLI test**

```python
def test_doctor_command_reports_status(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(
        "subprocess.run",
        lambda args, **kwargs: subprocess.CompletedProcess(args, 0, stdout="ok", stderr=""),
    )

    exit_code = main([
        "doctor",
        "--root",
        str(tmp_path),
        "--codex-command",
        "codex-test",
    ])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "codex-command" in captured.out
    assert "plugin-package" in captured.out
```

- [ ] **Step 2: Verify CLI test fails before wiring**

Run:

```powershell
python -m pytest tests/test_cli.py::test_doctor_command_reports_status -v
```

Expected: argparse rejects `doctor`.

- [ ] **Step 3: Add parser and `main` branch**

Add `doctor` subparser with `--root` and `--codex-command`. In `main`, call
`run_doctor(Path(args.root), codex_command=args.codex_command)`, print
`report.to_text()`, and return `0` or `1`.

- [ ] **Step 4: Verify CLI test passes**

Run:

```powershell
python -m pytest tests/test_cli.py::test_doctor_command_reports_status -v
```

Expected: test passes.

### Task 4: Documentation And Skill Copy

**Files:**
- Modify: `README.md`
- Modify: `docs/consumer-install.md`
- Modify: `docs/evaluation.md`
- Modify: `src/cdw/skill.py`
- Modify: `.agents/plugins/plugins/dynamic-workflows-for-codex/skills/dynamic-workflows-for-codex/SKILL.md`

- [ ] **Step 1: Update README**

Add `python -m cdw doctor` to Quickstart and add `cdw doctor` to "What You
Get". State that `doctor` is quota-free and validates the user's own Codex CLI.

- [ ] **Step 2: Update consumer install guide**

Put `python -m cdw doctor` before `live-smoke`, and describe `--adapter
codex-cli` as the default real clone-and-use path.

- [ ] **Step 3: Update skill copy**

Teach the packaged skill to run `cdw doctor` before live troubleshooting and to
prefer `--adapter codex-cli` for real workflows.

- [ ] **Step 4: Update evaluation checklist**

Add the v0.5 doctor behaviors and note that the command does not require
`OPENAI_API_KEY`.

### Task 5: Verification And Commit

**Files:**
- All changed files

- [ ] **Step 1: Run focused tests**

```powershell
python -m pytest tests/test_doctor.py tests/test_cli.py::test_doctor_command_reports_status -v
```

Expected: all selected tests pass.

- [ ] **Step 2: Run full tests**

```powershell
python -m pytest -v
```

Expected: full suite passes.

- [ ] **Step 3: Run local diagnostics**

```powershell
python -m cdw doctor
python -m cdw live-smoke
```

Expected: commands print diagnostic reports without traceback. `doctor` may
report local login/package issues depending on the machine; the important
contract is clear failure output without secrets or real worker execution.

- [ ] **Step 4: Commit**

```powershell
git add docs/superpowers/specs/2026-06-06-dynamic-workflows-for-Codex-v0.5-doctor.md docs/superpowers/plans/2026-06-06-dynamic-workflows-for-Codex-v0.5-doctor.md src/cdw/doctor.py src/cdw/cli.py tests/test_doctor.py tests/test_cli.py README.md docs/consumer-install.md docs/evaluation.md src/cdw/skill.py .agents/plugins/plugins/dynamic-workflows-for-codex/skills/dynamic-workflows-for-codex/SKILL.md
git commit -m "feat: add doctor diagnostics"
```
