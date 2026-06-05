from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from cdw.codex_mcp import LiveCodexAdapter
from cdw.schemas import WorkflowPlan, WorkUnit
from cdw.runtime import execute_plan


@dataclass
class CheckResult:
    name: str
    ok: bool
    message: str


@dataclass
class LiveSmokeReport:
    checks: list[CheckResult] = field(default_factory=list)
    run_id: str | None = None

    @property
    def ok(self) -> bool:
        return all(check.ok for check in self.checks)

    def to_text(self) -> str:
        lines = []
        for check in self.checks:
            status = "ok" if check.ok else "failed"
            lines.append(f"{check.name}: {status} - {check.message}")
        if self.run_id is not None:
            lines.append(f"run: {self.run_id}")
        return "\n".join(lines)


def run_live_smoke(root: Path, execute: bool = False) -> LiveSmokeReport:
    report = LiveSmokeReport()

    _check_import(report, "agents", "openai-agents package importable")
    _check_import(report, "openai", "openai package importable")
    codex_path = _check_codex_command(report)
    if codex_path is not None:
        _check_codex_version(report, codex_path)
    if execute:
        _check_openai_key(report)
        if report.ok:
            state = execute_plan(_live_smoke_plan(), root, LiveCodexAdapter(root=root))
            report.run_id = state.run_id
    return report


def _check_import(report: LiveSmokeReport, module_name: str, success: str) -> None:
    if importlib.util.find_spec(module_name) is None:
        report.checks.append(
            CheckResult(
                name=f"{module_name}-import",
                ok=False,
                message=f"{module_name} is not installed.",
            )
        )
        return
    report.checks.append(CheckResult(name=f"{module_name}-import", ok=True, message=success))


def _check_codex_command(report: LiveSmokeReport) -> str | None:
    codex_path = shutil.which("codex")
    if codex_path is None:
        report.checks.append(
            CheckResult(
                name="codex-command",
                ok=False,
                message="codex command not found on PATH.",
            )
        )
        return None
    report.checks.append(
        CheckResult(name="codex-command", ok=True, message=f"found {codex_path}")
    )
    return codex_path


def _check_codex_version(report: LiveSmokeReport, codex_path: str) -> None:
    try:
        completed = subprocess.run(
            [codex_path, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        report.checks.append(
            CheckResult(
                name="codex-version",
                ok=False,
                message=f"could not execute codex --version: {exc}",
            )
        )
        return

    output = (completed.stdout or completed.stderr).strip()
    if completed.returncode != 0:
        report.checks.append(
            CheckResult(
                name="codex-version",
                ok=False,
                message=output or f"codex exited with {completed.returncode}",
            )
        )
        return

    report.checks.append(
        CheckResult(name="codex-version", ok=True, message=output or "executable")
    )


def _check_openai_key(report: LiveSmokeReport) -> None:
    if os.environ.get("OPENAI_API_KEY"):
        report.checks.append(
            CheckResult(
                name="openai-api-key",
                ok=True,
                message="OPENAI_API_KEY is present.",
            )
        )
        return
    report.checks.append(
        CheckResult(
            name="openai-api-key",
            ok=False,
            message="OPENAI_API_KEY is not set.",
        )
    )


def _live_smoke_plan() -> WorkflowPlan:
    return WorkflowPlan(
        command="plan",
        request="Live smoke check",
        pattern="single-live-worker",
        verification_strategy="live-smoke",
        stop_condition="live_worker_verified",
        work_units=[
            WorkUnit(
                id="live-smoke",
                role="live smoke worker",
                goal="Confirm Codex MCP live worker can run",
                prompt="Return a one-sentence confirmation that the live worker ran.",
                expected_output="A concise live smoke confirmation.",
            )
        ],
    )
