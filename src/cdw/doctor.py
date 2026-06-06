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


def run_doctor(root: Path, codex_command: str | None = None) -> DoctorReport:
    report = DoctorReport()
    root = root.resolve()

    _check_runtime(report)
    _check_state_writable(report, root)
    resolution = resolve_codex_command(explicit=codex_command)
    if _check_codex_command(report, resolution):
        command = resolution.command or "codex"
        _check_codex_subcommand(
            report,
            "codex-version",
            [command, "--version"],
            "codex version available",
        )
        _check_codex_subcommand(
            report,
            "codex-login",
            [command, "login", "status"],
            "codex login status available",
        )
        _check_codex_subcommand(
            report,
            "codex-exec",
            [command, "exec", "--help"],
            "codex exec help available",
            use_output=False,
        )
    _check_plugin_package(report, root)
    _check_skill_package(report, root)
    return report


def _check_runtime(report: DoctorReport) -> None:
    report.checks.append(
        CheckResult(
            name="cdw-runtime",
            ok=True,
            message="cdw runtime importable",
        )
    )


def _check_state_writable(report: DoctorReport, root: Path) -> None:
    probe_path = root / ".cdw" / ".doctor-write-test"
    try:
        probe_path.parent.mkdir(parents=True, exist_ok=True)
        probe_path.write_text("ok", encoding="utf-8")
        probe_path.unlink()
    except OSError as exc:
        report.checks.append(
            CheckResult(
                name="cdw-state",
                ok=False,
                message=f".cdw state directory is not writable: {exc}",
            )
        )
        return
    report.checks.append(
        CheckResult(
            name="cdw-state",
            ok=True,
            message=".cdw state directory writable",
        )
    )


def _check_codex_command(
    report: DoctorReport,
    resolution: CodexCommandResolution,
) -> bool:
    if resolution.command is None:
        report.checks.append(
            CheckResult(
                name="codex-command",
                ok=False,
                message=(
                    "codex command not found on PATH. Set CDW_CODEX_COMMAND "
                    "or pass --codex-command with the user's Codex CLI path."
                ),
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


def _check_codex_subcommand(
    report: DoctorReport,
    name: str,
    args: list[str],
    fallback_message: str,
    use_output: bool = True,
) -> None:
    try:
        completed = subprocess.run(
            args,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        report.checks.append(
            CheckResult(
                name=name,
                ok=False,
                message=f"could not execute {' '.join(args[1:])}: {exc}",
            )
        )
        return

    output = (completed.stdout or completed.stderr).strip()
    if completed.returncode != 0:
        report.checks.append(
            CheckResult(
                name=name,
                ok=False,
                message=output or f"{' '.join(args[1:])} exited with {completed.returncode}",
            )
        )
        return

    report.checks.append(
        CheckResult(
            name=name,
            ok=True,
            message=output if use_output and output else fallback_message,
        )
    )


def _check_plugin_package(report: DoctorReport, root: Path) -> None:
    plugin_root = _plugin_root(root)
    marketplace_path = root / ".agents" / "plugins" / "marketplace.json"
    manifest_path = plugin_root / ".codex-plugin" / "plugin.json"
    missing = [
        str(path)
        for path in (marketplace_path, manifest_path)
        if not path.exists()
    ]
    if missing:
        report.checks.append(
            CheckResult(
                name="plugin-package",
                ok=False,
                message=f"missing repo-local plugin package files: {', '.join(missing)}",
            )
        )
        return
    report.checks.append(
        CheckResult(
            name="plugin-package",
            ok=True,
            message="repo-local plugin package present",
        )
    )


def _check_skill_package(report: DoctorReport, root: Path) -> None:
    skill_path = (
        _plugin_root(root)
        / "skills"
        / "dynamic-workflows-for-codex"
        / "SKILL.md"
    )
    if not skill_path.exists():
        report.checks.append(
            CheckResult(
                name="skill-package",
                ok=False,
                message=f"missing packaged skill: {skill_path}",
            )
        )
        return
    report.checks.append(
        CheckResult(
            name="skill-package",
            ok=True,
            message="packaged skill present",
        )
    )


def _plugin_root(root: Path) -> Path:
    return (
        root
        / ".agents"
        / "plugins"
        / "plugins"
        / "dynamic-workflows-for-codex"
    )
