from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from cdw.schemas import (
    VerificationResult,
    VerificationStatus,
    WorkerResult,
    WorkerStatus,
    WorkUnit,
)


class CodexAdapter(Protocol):
    def run_worker(self, work_unit: WorkUnit) -> WorkerResult:
        ...

    def verify_worker_result(self, result: WorkerResult) -> VerificationResult:
        ...


@dataclass
class FakeCodexAdapter:
    fail_work_unit_ids: set[str] = field(default_factory=set)

    def run_worker(self, work_unit: WorkUnit) -> WorkerResult:
        if work_unit.id in self.fail_work_unit_ids:
            return WorkerResult(
                work_unit_id=work_unit.id,
                status=WorkerStatus.FAILED,
                summary=f"{work_unit.id} failed",
                evidence=[],
                raw_output="simulated failure",
            )
        return WorkerResult(
            work_unit_id=work_unit.id,
            status=WorkerStatus.SUCCEEDED,
            summary=f"{work_unit.role} completed {work_unit.goal}",
            evidence=[work_unit.expected_output],
            raw_output=f"fake output for {work_unit.id}",
        )

    def verify_worker_result(self, result: WorkerResult) -> VerificationResult:
        if result.status == WorkerStatus.SUCCEEDED and result.evidence:
            return VerificationResult(
                work_unit_id=result.work_unit_id,
                status=VerificationStatus.PASSED,
                notes="Evidence present.",
            )
        return VerificationResult(
            work_unit_id=result.work_unit_id,
            status=VerificationStatus.FAILED,
            notes="Worker failed or returned no evidence.",
        )


@dataclass
class LiveCodexAdapter:
    root: str | Path

    def run_worker(self, work_unit: WorkUnit) -> WorkerResult:
        try:
            import agents  # noqa: F401
        except ImportError as exc:
            raise RuntimeError(
                "Live Codex MCP mode requires the optional 'live' dependencies: "
                "openai-agents, openai, and python-dotenv. Install with: "
                "pip install 'codex-dynamic-workflows[live]'."
            ) from exc
        raise NotImplementedError(
            "Live Codex MCP execution will be implemented after fake-runtime "
            "MVP verification."
        )

    def verify_worker_result(self, result: WorkerResult) -> VerificationResult:
        if result.status == WorkerStatus.SUCCEEDED and result.evidence:
            return VerificationResult(
                work_unit_id=result.work_unit_id,
                status=VerificationStatus.PASSED,
                notes="Evidence present.",
            )
        return VerificationResult(
            work_unit_id=result.work_unit_id,
            status=VerificationStatus.FAILED,
            notes="Worker failed or returned no evidence.",
        )
