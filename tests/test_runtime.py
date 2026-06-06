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


def test_runtime_persists_procedure_for_staged_run(tmp_path):
    bundle = _two_stage_bundle(on_failure="stop")

    state = execute_workflow_bundle(bundle, tmp_path, FakeCodexAdapter())
    loaded = load_run_state(tmp_path, state.run_id)

    assert state.procedure == bundle.procedure
    assert loaded.procedure == bundle.procedure


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
