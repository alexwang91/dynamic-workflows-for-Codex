from __future__ import annotations

from pathlib import Path

from cdw.artifacts import consumed_artifact_context, write_stage_artifacts
from cdw.boundaries import check_stage_boundaries
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
        constraints=bundle.constraints,
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
        if not _stage_dependencies_passed(state, state.procedure.stages, stage):
            break
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
        ensure_stage_boundary_result(root, state, stage)
        if _stage_boundary_failed(state, stage):
            break
        if _stage_gate_passed(state, stage):
            write_stage_artifacts(root, state, stage)
            save_run_state(root, state)
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
    artifact_context = consumed_artifact_context(root, state, stage)
    write_contract_context = _stage_write_contract_context(state, stage)
    for work_unit_id in stage.work_unit_ids:
        if work_unit_id in completed:
            continue
        work_unit = work_units[work_unit_id]
        prompt_parts = [work_unit.prompt]
        if artifact_context:
            prompt_parts.append(
                "Use these verified upstream artifacts as context:\n"
                f"{artifact_context}"
            )
        if write_contract_context:
            prompt_parts.append(write_contract_context)
        if len(prompt_parts) > 1:
            work_unit = work_unit.model_copy(
                update={
                    "prompt": "\n\n".join(prompt_parts)
                }
            )
        worker_result = adapter.run_worker(work_unit)
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


def ensure_stage_boundary_result(
    root: Path,
    state: RunState,
    stage: WorkflowStage,
) -> RunState:
    if not _stage_requires_boundary_check(stage):
        return state
    if any(result.stage_id == stage.id for result in state.boundary_results):
        return state
    boundary_result = check_stage_boundaries(
        state.constraints,
        stage,
        _stage_worker_results(state, stage),
    )
    state.boundary_results.append(boundary_result)
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


def _stage_dependencies_passed(
    state: RunState,
    stages: list[WorkflowStage],
    stage: WorkflowStage,
) -> bool:
    if not stage.depends_on:
        return True

    stages_by_id = {candidate.id: candidate for candidate in stages}
    return all(
        _stage_gate_passed(state, stages_by_id[dependency_id])
        for dependency_id in stage.depends_on
    )


def _stage_boundary_failed(state: RunState, stage: WorkflowStage) -> bool:
    return any(
        result.stage_id == stage.id and result.status == "failed"
        for result in state.boundary_results
    )


def _stage_requires_boundary_check(stage: WorkflowStage) -> bool:
    return stage.write_policy in {"guarded", "write-heavy"}


def _stage_write_contract_context(state: RunState, stage: WorkflowStage) -> str:
    if not state.constraints.requires_write_contract:
        return ""
    if not _stage_requires_boundary_check(stage):
        return ""

    allowed_paths = ", ".join(state.constraints.allowed_paths) or (
        "any relative path not forbidden"
    )
    forbidden_paths = ", ".join(state.constraints.forbidden_paths) or "none"
    return (
        "This guarded/write-heavy stage must declare planned writes with a "
        "machine-readable section before any write phase can proceed.\n"
        "Use this exact shape:\n"
        "WRITE_CONTRACT:\n"
        '{"paths":[{"path":"relative/path.py","action":"modify",'
        '"reason":"why this path is in scope"}],'
        '"checks":["python -m pytest"]}\n'
        f"allowed paths: {allowed_paths}\n"
        f"forbidden paths: {forbidden_paths}"
    )


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


def _stage_worker_results(
    state: RunState,
    stage: WorkflowStage,
) -> list:
    stage_ids = set(stage.work_unit_ids)
    return [
        result for result in state.worker_results if result.work_unit_id in stage_ids
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
    unresolved.extend(
        f"boundary:{boundary.stage_id}:{violation.path}"
        for boundary in state.boundary_results
        if boundary.status == "failed"
        for violation in boundary.violations
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
