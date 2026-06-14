from cdw.codex_mcp import FakeCodexAdapter
from cdw.artifacts import read_artifact
from cdw.planner import build_plan
from cdw.resume import resume_run
from cdw.runtime import execute_plan, execute_workflow_bundle
from cdw.schemas import (
    VerificationResult,
    WorkerResult,
    WorkerStatus,
    WorkflowPlan,
    WorkflowProcedure,
    WorkflowSpecBundle,
    WorkflowSpecConstraints,
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


def test_runtime_writes_artifacts_for_passed_stage(tmp_path):
    bundle = _dependent_stage_bundle(on_failure="continue")

    state = execute_workflow_bundle(bundle, tmp_path, FakeCodexAdapter())

    assert len(state.artifacts) == 1
    assert state.artifacts[0].name == "first artifact"
    artifact_path = tmp_path / ".cdw" / "runs" / state.run_id / state.artifacts[0].path
    assert artifact_path.exists()
    assert "first worker completed Run first stage" in artifact_path.read_text(
        encoding="utf-8"
    )


def test_runtime_does_not_write_artifacts_for_failed_stage(tmp_path):
    bundle = _dependent_stage_bundle(on_failure="continue")
    adapter = FakeCodexAdapter(fail_work_unit_ids={"first"})

    state = execute_workflow_bundle(bundle, tmp_path, adapter)

    assert state.artifacts == []


def test_runtime_hydrates_consumed_artifacts_into_dependent_worker_prompt(tmp_path):
    bundle = _dependent_stage_bundle(on_failure="continue")
    adapter = RecordingAdapter()

    execute_workflow_bundle(bundle, tmp_path, adapter)

    prompts = dict(adapter.prompts)
    assert "Consumed artifacts" in prompts["second"]
    assert "first artifact" in prompts["second"]
    assert "summary for first" in prompts["second"]


def test_resume_does_not_duplicate_existing_artifact_records(tmp_path):
    bundle = _dependent_stage_bundle(on_failure="continue")
    state = execute_workflow_bundle(bundle, tmp_path, FakeCodexAdapter())

    resumed = resume_run(tmp_path, state.run_id, FakeCodexAdapter())

    assert len(resumed.artifacts) == 1
    assert resumed.artifacts[0].name == "first artifact"


def test_runtime_records_passing_boundary_for_guarded_stage_after_approval(tmp_path):
    bundle = _boundary_bundle(allowed_paths=["src/**"])
    state = execute_workflow_bundle(
        bundle,
        tmp_path,
        BoundaryAdapter({"inventory": "Inventory complete"}),
    )

    resumed = resume_run(
        tmp_path,
        state.run_id,
        BoundaryAdapter({"patch-plan": "WRITE_PATHS:\n- src/users.py"}),
        approve_human_gates=True,
    )

    assert resumed.synthesis is not None
    assert resumed.synthesis.status == "complete"
    assert len(resumed.boundary_results) == 1
    assert resumed.boundary_results[0].status == "passed"
    assert resumed.boundary_results[0].checked_paths == ["src/users.py"]
    assert any(artifact.name == "guarded patch plan" for artifact in resumed.artifacts)


def test_runtime_boundary_failure_blocks_guarded_stage_artifact(tmp_path):
    bundle = _boundary_bundle(allowed_paths=["src/**"], forbidden_paths=["secrets/**"])
    state = execute_workflow_bundle(
        bundle,
        tmp_path,
        BoundaryAdapter({"inventory": "Inventory complete"}),
    )

    resumed = resume_run(
        tmp_path,
        state.run_id,
        BoundaryAdapter({"patch-plan": "WRITE_PATHS:\n- secrets/key.py"}),
        approve_human_gates=True,
    )

    assert resumed.synthesis is not None
    assert resumed.synthesis.status == "incomplete"
    assert len(resumed.boundary_results) == 1
    assert resumed.boundary_results[0].status == "failed"
    assert resumed.boundary_results[0].violations[0].path == "secrets/key.py"
    assert "boundary:migration-plan-review:secrets/key.py" in resumed.synthesis.unresolved
    assert not any(
        artifact.name == "guarded patch plan" for artifact in resumed.artifacts
    )


def test_runtime_injects_write_contract_instruction_for_required_guarded_stage(
    tmp_path,
):
    bundle = _boundary_bundle(
        allowed_paths=["src/**"],
        requires_write_contract=True,
    )
    state = execute_workflow_bundle(
        bundle,
        tmp_path,
        BoundaryAdapter({"inventory": "Inventory complete"}),
    )
    adapter = RecordingAdapter()

    resume_run(
        tmp_path,
        state.run_id,
        adapter,
        approve_human_gates=True,
    )

    prompts = dict(adapter.prompts)
    assert "WRITE_CONTRACT:" in prompts["patch-plan"]
    assert '"paths"' in prompts["patch-plan"]
    assert "allowed paths: src/**" in prompts["patch-plan"]


def test_runtime_missing_required_write_contract_blocks_guarded_stage_artifact(
    tmp_path,
):
    bundle = _boundary_bundle(
        allowed_paths=["src/**"],
        requires_write_contract=True,
    )
    state = execute_workflow_bundle(
        bundle,
        tmp_path,
        BoundaryAdapter({"inventory": "Inventory complete"}),
    )

    resumed = resume_run(
        tmp_path,
        state.run_id,
        BoundaryAdapter({"patch-plan": "WRITE_PATHS:\n- src/users.py"}),
        approve_human_gates=True,
    )

    assert resumed.synthesis is not None
    assert resumed.synthesis.status == "incomplete"
    assert resumed.boundary_results[0].violations[0].reason == (
        "missing_write_contract"
    )
    assert not any(
        artifact.name == "guarded patch plan" for artifact in resumed.artifacts
    )


def test_runtime_writes_write_phase_draft_for_structured_contract(tmp_path):
    bundle = _boundary_bundle(
        allowed_paths=["src/**"],
        requires_write_contract=True,
    )
    state = execute_workflow_bundle(
        bundle,
        tmp_path,
        BoundaryAdapter({"inventory": "Inventory complete"}),
    )
    contract = (
        'WRITE_CONTRACT:\n{"paths":[{"path":"src/users.py",'
        '"action":"modify","reason":"Rename User model to Account"}],'
        '"checks":["python -m pytest tests/test_users.py"]}'
    )

    resumed = resume_run(
        tmp_path,
        state.run_id,
        BoundaryAdapter({"patch-plan": contract}),
        approve_human_gates=True,
    )
    resumed_again = resume_run(
        tmp_path,
        state.run_id,
        BoundaryAdapter({}),
        approve_human_gates=True,
    )

    drafts = [
        artifact
        for artifact in resumed_again.artifacts
        if artifact.name == "write phase draft"
    ]
    assert resumed.synthesis is not None
    assert resumed.synthesis.status == "complete"
    assert len(drafts) == 1
    content = read_artifact(
        tmp_path,
        resumed_again,
        "write phase draft",
        stage_id="migration-plan-review",
    )
    assert "src/users.py" in content
    assert "Rename User model to Account" in content
    assert "python -m pytest tests/test_users.py" in content
    assert "does not apply patches" in content


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


class RecordingAdapter:
    def __init__(self):
        self.prompts = []

    def run_worker(self, work_unit):
        self.prompts.append((work_unit.id, work_unit.prompt))
        return WorkerResult(
            work_unit_id=work_unit.id,
            status=WorkerStatus.SUCCEEDED,
            summary=f"summary for {work_unit.id}",
            evidence=[work_unit.prompt],
            raw_output=work_unit.prompt,
        )

    def verify_worker_result(self, result):
        return VerificationResult(
            work_unit_id=result.work_unit_id,
            status="passed",
            notes="ok",
        )


class BoundaryAdapter:
    def __init__(self, outputs):
        self.outputs = outputs

    def run_worker(self, work_unit):
        output = self.outputs.get(work_unit.id, f"{work_unit.id} complete")
        return WorkerResult(
            work_unit_id=work_unit.id,
            status=WorkerStatus.SUCCEEDED,
            summary=output,
            evidence=[output],
            raw_output=output,
        )

    def verify_worker_result(self, result):
        return VerificationResult(
            work_unit_id=result.work_unit_id,
            status="passed",
            notes="ok",
        )


def _boundary_bundle(
    allowed_paths: list[str],
    forbidden_paths: list[str] | None = None,
    requires_write_contract: bool = False,
) -> WorkflowSpecBundle:
    plan = WorkflowPlan(
        command="migrate",
        request="Rename User model to Account",
        pattern="guarded-migration",
        work_units=[
            WorkUnit(
                id="inventory",
                role="inventory worker",
                goal="Inventory migration scope",
                prompt="Inventory migration scope",
                expected_output="Inventory result",
            ),
            WorkUnit(
                id="patch-plan",
                role="patch planner",
                goal="Plan guarded patch",
                prompt="Plan guarded patch",
                expected_output="Patch plan",
            ),
        ],
        verification_strategy="stage-gates",
        stop_condition="procedure_complete",
    )
    return WorkflowSpecBundle(
        constraints=WorkflowSpecConstraints(
            write_policy="write-heavy",
            allowed_paths=allowed_paths,
            forbidden_paths=forbidden_paths or [],
            requires_human_approval=True,
            requires_write_contract=requires_write_contract,
        ),
        procedure=WorkflowProcedure(
            mode="guarded",
            triggers=["migrate"],
            stages=[
                WorkflowStage(
                    id="migration-inventory",
                    purpose="Inventory",
                    work_unit_ids=["inventory"],
                    produces=["migration inventory"],
                ),
                WorkflowStage(
                    id="migration-plan-review",
                    purpose="Guarded patch review",
                    work_unit_ids=["patch-plan"],
                    depends_on=["migration-inventory"],
                    consumes=["migration inventory"],
                    produces=["guarded patch plan"],
                    gate="manual_review",
                    on_failure="require_human",
                    write_policy="guarded",
                ),
            ],
            final_artifacts=["synthesis report"],
        ),
        plan=plan,
    )


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
