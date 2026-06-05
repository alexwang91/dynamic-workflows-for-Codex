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

    ensure_worker_results(root, state, adapter)
    ensure_verification_results(root, state, adapter)
    finalize_synthesis(root, state)
    return state


def ensure_worker_results(
    root: Path, state: RunState, adapter: CodexAdapter
) -> RunState:
    completed = {result.work_unit_id for result in state.worker_results}
    for work_unit in state.plan.work_units:
        if work_unit.id in completed:
            continue
        worker_result = adapter.run_worker(work_unit)
        state.worker_results.append(worker_result)
        save_run_state(root, state)
    return state


def ensure_verification_results(
    root: Path, state: RunState, adapter: CodexAdapter
) -> RunState:
    completed = {result.work_unit_id for result in state.verification_results}
    for worker_result in state.worker_results:
        if worker_result.work_unit_id in completed:
            continue
        verification = adapter.verify_worker_result(worker_result)
        state.verification_results.append(verification)
        save_run_state(root, state)
    return state


def finalize_synthesis(root: Path, state: RunState) -> RunState:
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
