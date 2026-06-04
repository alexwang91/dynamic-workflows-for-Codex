from __future__ import annotations

from pathlib import Path

from cdw.codex_mcp import CodexAdapter
from cdw.schemas import (
    RunState,
    SynthesisReport,
    VerificationStatus,
    WorkflowPlan,
    WorkerStatus,
)
from cdw.state import create_run_state, save_run_state


def execute_plan(plan: WorkflowPlan, root: Path, adapter: CodexAdapter) -> RunState:
    state = create_run_state(plan)
    save_run_state(root, state)

    for work_unit in plan.work_units:
        worker_result = adapter.run_worker(work_unit)
        state.worker_results.append(worker_result)
        save_run_state(root, state)

    for worker_result in state.worker_results:
        verification = adapter.verify_worker_result(worker_result)
        state.verification_results.append(verification)
        save_run_state(root, state)

    state.synthesis = _synthesize(state)
    save_run_state(root, state)
    return state


def _synthesize(state: RunState) -> SynthesisReport:
    unresolved = [
        result.work_unit_id
        for result in state.worker_results
        if result.status == WorkerStatus.FAILED
    ]
    unresolved.extend(
        verification.work_unit_id
        for verification in state.verification_results
        if verification.status == VerificationStatus.FAILED
        and verification.work_unit_id not in unresolved
    )

    if unresolved:
        return SynthesisReport(
            status="incomplete",
            summary="Workflow completed with unresolved work units.",
            findings=[result.summary for result in state.worker_results],
            unresolved=unresolved,
        )

    return SynthesisReport(
        status="complete",
        summary="Workflow completed after worker execution and verification.",
        findings=[result.summary for result in state.worker_results],
    )
