from __future__ import annotations

import importlib.util
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from cdw.codex_mcp import LiveCodexAdapter
from cdw.codex_command import CodexCommandResolution, resolve_codex_command
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


def run_live_smoke(
    root: Path,
    execute: bool = False,
    codex_command: str | None = None,
) -> LiveSmokeReport:
    report = LiveSmokeReport()

    _check_import(report, "agents", "openai-agents package importable")
    _check_import(report, "openai", "openai package importable")
    resolution = resolve_codex_command(explicit=codex_command)
    if _check_codex_command(report, resolution):
        _check_codex_version(report, resolution.command or "codex")
    if execute:
        _check_openai_key(report)
        if report.ok:
            try:
                state = execute_plan(
                    _live_smoke_plan(),
                    root,
                    LiveCodexAdapter(
                        root=root,
                        codex_command=resolution.command or "codex",
                    ),
                )
            except Exception as exc:
                report.checks.append(
                    CheckResult(
                        name="live-run",
                        ok=False,
                        message=str(exc) or exc.__class__.__name__,
                    )
                )
            else:
                report.checks.append(
                    CheckResult(
                        name="live-run",
                        ok=True,
                        message="live worker completed.",
                    )
                )
                report.run_id = state.run_id
    return report


def build_live_smoke_contract(root: Path) -> dict[str, object]:
    plan = _live_smoke_plan()
    adapter = LiveCodexAdapter(root=root)
    work_unit = plan.work_units[0]
    return adapter._codex_mcp_tool_contract(adapter._worker_task_prompt(work_unit))


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


def _check_codex_command(
    report: LiveSmokeReport,
    resolution: CodexCommandResolution,
) -> bool:
    if resolution.command is None:
        report.checks.append(
            CheckResult(
                name="codex-command",
                ok=False,
                message="codex command not found on PATH.",
            )
        )
        return False
    report.checks.append(
        CheckResult(
            name="codex-command",
            ok=True,
            message=f"source={resolution.source} command={resolution.command}",
        )
    )
    return True


def _check_codex_version(report: LiveSmokeReport, codex_path: str) -> None:
    try:
        completed = subprocess.run(
            [codex_path, "--version"],
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        report.checks.append(
            CheckResult(
                name="codex-version",
                ok=False,
                message=_codex_version_error_message(codex_path, exc),
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


def _codex_version_error_message(codex_path: str, exc: BaseException) -> str:
    message = f"could not execute codex --version: {exc}"
    if "WindowsApps" in codex_path and isinstance(exc, PermissionError):
        return (
            f"{message}. Hint: set CDW_CODEX_COMMAND or pass --codex-command "
            "with a directly executable Codex CLI path."
        )
    return message


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
