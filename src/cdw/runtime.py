from __future__ import annotations

from pathlib import Path

from cdw.codex_mcp import CodexAdapter
from cdw.schemas import (
    RunState,
    SynthesisReport,
    VerificationResult,
    VerificationStatus,
    WorkflowPlan,
    WorkflowSpecBundle,
    WorkflowStage,
    WorkerStatus,
)
from cdw.state import create_run_state, save_run_state
from cdw.workflow_spec import build_workflow_spec_bundle


def execute_plan(
    plan: WorkflowPlan,
    root: Path,
    adapter: CodexAdapter,
    approve_human_gates: bool = False,
    adapter_name: str | None = None,
) -> RunState:
    return execute_workflow_bundle(
        build_workflow_spec_bundle(plan),
        root,
        adapter,
        approve_human_gates=approve_human_gates,
        adapter_name=adapter_name,
    )


def execute_workflow_bundle(
    bundle: WorkflowSpecBundle,
    root: Path,
    adapter: CodexAdapter,
    approve_human_gates: bool = False,
    adapter_name: str | None = None,
) -> RunState:
    state = create_run_state(
        bundle.plan,
        procedure=bundle.procedure,
        adapter=adapter_name,
    )
    save_run_state(root, state)

    execute_existing_state(
        root,
        state,
        adapter,
        approve_human_gates=approve_human_gates,
    )
    return state


def execute_existing_state(
    root: Path,
    state: RunState,
    adapter: CodexAdapter,
    approve_human_gates: bool = False,
) -> RunState:
    if state.procedure is not None:
        ensure_procedure_results(
            root,
            state,
            adapter,
            approve_human_gates=approve_human_gates,
        )
        finalize_synthesis(root, state)
        return state

    ensure_worker_results(root, state, adapter)
    ensure_verification_results(root, state, adapter)
    finalize_synthesis(root, state)
    return state


def ensure_procedure_results(
    root: Path,
    state: RunState,
    adapter: CodexAdapter,
    approve_human_gates: bool = False,
) -> RunState:
    if state.procedure is None:
        return state

    for stage in state.procedure.stages:
        if _stage_requires_human_approval(stage) and not _stage_gate_passed(
            state,
            stage,
        ):
            if state.pending_human_approval == stage.id:
                if not approve_human_gates:
                    save_run_state(root, state)
                    break
                state.pending_human_approval = None
                save_run_state(root, state)
            else:
                state.pending_human_approval = stage.id
                save_run_state(root, state)
                break
        ensure_stage_worker_results(root, state, adapter, stage)
        ensure_stage_verification_results(root, state, adapter, stage)
        if _stage_gate_passed(state, stage):
            continue
        if stage.on_failure != "continue":
            break
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


def ensure_stage_worker_results(
    root: Path,
    state: RunState,
    adapter: CodexAdapter,
    stage: WorkflowStage,
) -> RunState:
    completed = {result.work_unit_id for result in state.worker_results}
    work_units = {work_unit.id: work_unit for work_unit in state.plan.work_units}
    for work_unit_id in stage.work_unit_ids:
        if work_unit_id in completed:
            continue
        worker_result = adapter.run_worker(work_units[work_unit_id])
        state.worker_results.append(worker_result)
        save_run_state(root, state)
    return state


def ensure_stage_verification_results(
    root: Path,
    state: RunState,
    adapter: CodexAdapter,
    stage: WorkflowStage,
) -> RunState:
    completed = {result.work_unit_id for result in state.verification_results}
    stage_ids = set(stage.work_unit_ids)
    for worker_result in state.worker_results:
        if worker_result.work_unit_id not in stage_ids:
            continue
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


def _stage_gate_passed(state: RunState, stage: WorkflowStage) -> bool:
    passed_ids = {
        result.work_unit_id
        for result in _stage_verification_results(state, stage)
        if result.status == VerificationStatus.PASSED
    }
    if stage.gate == "any_verified":
        return any(work_unit_id in passed_ids for work_unit_id in stage.work_unit_ids)

    if stage.gate == "manual_review":
        return all(work_unit_id in passed_ids for work_unit_id in stage.work_unit_ids)

    required_ids = [
        work_unit.id
        for work_unit in state.plan.work_units
        if work_unit.id in stage.work_unit_ids and work_unit.required
    ]
    if not required_ids:
        required_ids = stage.work_unit_ids
    return all(work_unit_id in passed_ids for work_unit_id in required_ids)


def _stage_requires_human_approval(stage: WorkflowStage) -> bool:
    return stage.gate == "manual_review" or stage.on_failure == "require_human"


def _stage_verification_results(
    state: RunState,
    stage: WorkflowStage,
) -> list[VerificationResult]:
    stage_ids = set(stage.work_unit_ids)
    return [
        result
        for result in state.verification_results
        if result.work_unit_id in stage_ids
    ]


def _synthesize(state: RunState) -> SynthesisReport:
    if state.pending_human_approval:
        return SynthesisReport(
            status="waiting_for_human",
            summary="Workflow is waiting for human approval before continuing.",
            findings=[result.summary for result in state.worker_results],
            unresolved=[state.pending_human_approval],
        )

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
