from cdw.codex_mcp import FakeCodexAdapter
from cdw.planner import build_plan
from cdw.resume import resume_run
from cdw.runtime import execute_plan, execute_workflow_bundle
from cdw.schemas import (
    WorkflowPlan,
    WorkflowProcedure,
    WorkflowSpecBundle,
    WorkflowStage,
    WorkUnit,
)
from cdw.state import load_run_state


def test_runtime_verifies_before_synthesis(tmp_path):
    plan = build_plan("review", "Review this branch")
    adapter = FakeCodexAdapter()

    state = execute_plan(plan, tmp_path, adapter)

    assert len(state.worker_results) == len(plan.work_units)
    assert len(state.verification_results) == len(plan.work_units)
    assert state.synthesis is not None
    assert state.synthesis.status == "complete"
    assert all(result.status == "passed" for result in state.verification_results)


def test_runtime_marks_incomplete_when_required_worker_fails(tmp_path):
    plan = build_plan("review", "Review this branch")
    adapter = FakeCodexAdapter(fail_work_unit_ids={"security"})

    state = execute_plan(plan, tmp_path, adapter)

    assert state.synthesis is not None
    assert state.synthesis.status == "incomplete"
    assert "security" in state.synthesis.unresolved


def test_runtime_stops_before_later_stage_when_stage_gate_fails(tmp_path):
    bundle = _two_stage_bundle(on_failure="stop")
    adapter = FakeCodexAdapter(fail_work_unit_ids={"first"})

    state = execute_workflow_bundle(bundle, tmp_path, adapter)

    assert [result.work_unit_id for result in state.worker_results] == ["first"]
    assert state.synthesis is not None
    assert state.synthesis.status == "incomplete"
    assert "first" in state.synthesis.unresolved


def test_runtime_continues_later_stage_when_stage_allows_failure(tmp_path):
    bundle = _two_stage_bundle(on_failure="continue")
    adapter = FakeCodexAdapter(fail_work_unit_ids={"first"})

    state = execute_workflow_bundle(bundle, tmp_path, adapter)

    assert [result.work_unit_id for result in state.worker_results] == [
        "first",
        "second",
    ]
    assert state.synthesis is not None
    assert state.synthesis.status == "incomplete"
    assert "first" in state.synthesis.unresolved


def test_runtime_stops_dependent_stage_when_dependency_gate_fails(tmp_path):
    bundle = _dependent_stage_bundle(on_failure="continue")
    adapter = FakeCodexAdapter(fail_work_unit_ids={"first"})

    state = execute_workflow_bundle(bundle, tmp_path, adapter)

    assert [result.work_unit_id for result in state.worker_results] == ["first"]
    assert state.synthesis is not None
    assert state.synthesis.status == "incomplete"
    assert "first" in state.synthesis.unresolved


def test_runtime_persists_procedure_for_staged_run(tmp_path):
    bundle = _two_stage_bundle(on_failure="stop")

    state = execute_workflow_bundle(bundle, tmp_path, FakeCodexAdapter())
    loaded = load_run_state(tmp_path, state.run_id)

    assert state.procedure == bundle.procedure
    assert loaded.procedure == bundle.procedure


def test_runtime_waits_before_manual_review_stage(tmp_path):
    bundle = _manual_gate_bundle()

    state = execute_workflow_bundle(bundle, tmp_path, FakeCodexAdapter())

    assert [result.work_unit_id for result in state.worker_results] == ["first"]
    assert state.pending_human_approval == "manual-review"
    assert state.synthesis is not None
    assert state.synthesis.status == "waiting_for_human"
    assert "manual-review" in state.synthesis.unresolved


def test_runtime_does_not_preapprove_new_manual_review_stage(tmp_path):
    bundle = _manual_gate_bundle()

    state = execute_workflow_bundle(
        bundle,
        tmp_path,
        FakeCodexAdapter(),
        approve_human_gates=True,
    )

    assert [result.work_unit_id for result in state.worker_results] == ["first"]
    assert state.pending_human_approval == "manual-review"
    assert state.synthesis is not None
    assert state.synthesis.status == "waiting_for_human"


def test_resume_preserves_staged_stop_behavior(tmp_path):
    bundle = _two_stage_bundle(on_failure="stop")
    state = execute_workflow_bundle(
        bundle,
        tmp_path,
        FakeCodexAdapter(fail_work_unit_ids={"first"}),
    )

    resumed = resume_run(tmp_path, state.run_id, FakeCodexAdapter())

    assert [result.work_unit_id for result in resumed.worker_results] == ["first"]
    assert resumed.synthesis is not None
    assert resumed.synthesis.status == "incomplete"


def test_resume_can_continue_after_human_approval(tmp_path):
    bundle = _manual_gate_bundle()
    state = execute_workflow_bundle(bundle, tmp_path, FakeCodexAdapter())

    resumed = resume_run(
        tmp_path,
        state.run_id,
        FakeCodexAdapter(),
        approve_human_gates=True,
    )

    assert [result.work_unit_id for result in resumed.worker_results] == [
        "first",
        "second",
    ]
    assert resumed.pending_human_approval is None
    assert resumed.synthesis is not None
    assert resumed.synthesis.status == "complete"


def test_approval_only_releases_current_pending_stage(tmp_path):
    bundle = _double_manual_gate_bundle()
    state = execute_workflow_bundle(bundle, tmp_path, FakeCodexAdapter())

    first_resume = resume_run(
        tmp_path,
        state.run_id,
        FakeCodexAdapter(),
        approve_human_gates=True,
    )

    assert [result.work_unit_id for result in first_resume.worker_results] == [
        "first",
        "second",
    ]
    assert first_resume.pending_human_approval == "manual-review-two"
    assert first_resume.synthesis is not None
    assert first_resume.synthesis.status == "waiting_for_human"

    second_resume = resume_run(
        tmp_path,
        state.run_id,
        FakeCodexAdapter(),
        approve_human_gates=True,
    )

    assert [result.work_unit_id for result in second_resume.worker_results] == [
        "first",
        "second",
        "third",
    ]
    assert second_resume.pending_human_approval is None
    assert second_resume.synthesis is not None
    assert second_resume.synthesis.status == "complete"


def _two_stage_bundle(on_failure: str) -> WorkflowSpecBundle:
    plan = WorkflowPlan(
        command="review",
        request="Run staged workflow",
        pattern="two-stage",
        work_units=[
            WorkUnit(
                id="first",
                role="first worker",
                goal="Run first stage",
                prompt="Run first stage",
                expected_output="First result",
            ),
            WorkUnit(
                id="second",
                role="second worker",
                goal="Run second stage",
                prompt="Run second stage",
                expected_output="Second result",
            ),
        ],
        verification_strategy="stage-gates",
        stop_condition="procedure_complete",
    )
    return WorkflowSpecBundle(
        procedure=WorkflowProcedure(
            mode="sequence",
            triggers=["staged"],
            stages=[
                WorkflowStage(
                    id="stage-one",
                    purpose="Run first stage",
                    work_unit_ids=["first"],
                    gate="all_required_verified",
                    on_failure=on_failure,
                ),
                WorkflowStage(
                    id="stage-two",
                    purpose="Run second stage",
                    work_unit_ids=["second"],
                    gate="all_required_verified",
                    on_failure="stop",
                ),
            ],
            final_artifacts=["synthesis report"],
        ),
        plan=plan,
    )


def _manual_gate_bundle() -> WorkflowSpecBundle:
    bundle = _two_stage_bundle(on_failure="stop")
    assert bundle.procedure is not None
    bundle.procedure.stages[1] = WorkflowStage(
        id="manual-review",
        purpose="Require human approval before second stage",
        work_unit_ids=["second"],
        gate="manual_review",
        on_failure="require_human",
    )
    return bundle


def _dependent_stage_bundle(on_failure: str) -> WorkflowSpecBundle:
    bundle = _two_stage_bundle(on_failure=on_failure)
    assert bundle.procedure is not None
    bundle.procedure.stages[0].produces = ["first artifact"]
    bundle.procedure.stages[1].depends_on = ["stage-one"]
    bundle.procedure.stages[1].consumes = ["first artifact"]
    return bundle


def _double_manual_gate_bundle() -> WorkflowSpecBundle:
    plan = WorkflowPlan(
        command="review",
        request="Run double manual workflow",
        pattern="double-manual",
        work_units=[
            WorkUnit(
                id="first",
                role="first worker",
                goal="Run first stage",
                prompt="Run first stage",
                expected_output="First result",
            ),
            WorkUnit(
                id="second",
                role="second worker",
                goal="Run second stage",
                prompt="Run second stage",
                expected_output="Second result",
            ),
            WorkUnit(
                id="third",
                role="third worker",
                goal="Run third stage",
                prompt="Run third stage",
                expected_output="Third result",
            ),
        ],
        verification_strategy="stage-gates",
        stop_condition="procedure_complete",
    )
    return WorkflowSpecBundle(
        procedure=WorkflowProcedure(
            mode="sequence",
            triggers=["staged"],
            stages=[
                WorkflowStage(
                    id="stage-one",
                    purpose="Run first stage",
                    work_unit_ids=["first"],
                    gate="all_required_verified",
                    on_failure="stop",
                ),
                WorkflowStage(
                    id="manual-review-one",
                    purpose="Require human approval before second stage",
                    work_unit_ids=["second"],
                    gate="manual_review",
                    on_failure="require_human",
                ),
                WorkflowStage(
                    id="manual-review-two",
                    purpose="Require human approval before third stage",
                    work_unit_ids=["third"],
                    gate="manual_review",
                    on_failure="require_human",
                ),
            ],
            final_artifacts=["synthesis report"],
        ),
        plan=plan,
    )
