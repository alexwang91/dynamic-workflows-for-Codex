from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from cdw.schemas import (
    VerificationResult,
    VerificationStatus,
    WorkerResult,
    WorkerStatus,
    WorkUnit,
)


@dataclass
class CodexCliAdapter:
    root: str | Path
    sandbox: str = "workspace-write"
    approval_policy: str = "never"
    timeout_seconds: int = 3600
    codex_command: str = "codex"

    def run_worker(self, work_unit: WorkUnit) -> WorkerResult:
        output = self._run_codex(self._worker_task_prompt(work_unit))
        return WorkerResult(
            work_unit_id=work_unit.id,
            status=WorkerStatus.SUCCEEDED,
            summary=output,
            evidence=[output],
            raw_output=output,
        )

    def verify_worker_result(self, result: WorkerResult) -> VerificationResult:
        output = self._run_codex(self._verifier_task_prompt(result))
        first_line = output.strip().splitlines()[0].upper() if output.strip() else ""
        if first_line.startswith("PASSED"):
            return VerificationResult(
                work_unit_id=result.work_unit_id,
                status=VerificationStatus.PASSED,
                notes=output,
            )
        return VerificationResult(
            work_unit_id=result.work_unit_id,
            status=VerificationStatus.FAILED,
            notes=output or "Verifier returned no output.",
        )

    def _run_codex(self, prompt: str) -> str:
        args = [
            self.codex_command,
            "exec",
            "-C",
            str(Path(self.root)),
            "-s",
            self.sandbox,
            prompt,
        ]
        try:
            completed = subprocess.run(
                args,
                capture_output=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.timeout_seconds,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise RuntimeError(
                f"Codex CLI adapter could not run codex exec: {exc}"
            ) from exc

        output = _clean_codex_output(completed.stdout or completed.stderr)
        if completed.returncode != 0:
            message = output or f"codex exec exited with {completed.returncode}"
            raise RuntimeError(f"Codex CLI adapter failed: {message}")
        if not output:
            raise RuntimeError("Codex CLI adapter returned no output.")
        return output

    def _worker_task_prompt(self, work_unit: WorkUnit) -> str:
        return (
            f"Role: {work_unit.role}\n"
            f"Goal: {work_unit.goal}\n"
            f"Task: {work_unit.prompt}\n"
            f"Expected output: {work_unit.expected_output}\n"
            "Return a concise structured result with evidence."
        )

    def _verifier_task_prompt(self, result: WorkerResult) -> str:
        return (
            "Verify this worker result adversarially.\n"
            "First line must be exactly `PASSED` or `FAILED`.\n"
            f"Worker result status: {result.status}\n"
            f"Summary: {result.summary}\n"
            f"Evidence: {result.evidence}\n"
            f"Raw output: {result.raw_output}\n"
        )


def _clean_codex_output(output: str) -> str:
    lines = []
    for line in output.splitlines():
        stripped = line.strip()
        if (
            stripped.startswith("SUCCESS: The process with PID ")
            and stripped.endswith(" has been terminated.")
        ):
            continue
        lines.append(line)
    return "\n".join(lines).strip()
