from cdw.artifacts import read_artifact
from cdw.planner import build_plan
from cdw.schemas import BoundaryResult, WorkflowStage, WritePathIntent
from cdw.state import create_run_state
from cdw.write_drafts import (
    WRITE_PHASE_DRAFT_ARTIFACT_NAME,
    write_phase_draft_artifact,
)


def test_write_phase_draft_persists_markdown_and_updates_index(tmp_path):
    state = create_run_state(build_plan("migrate", "Rename User model to Account"))
    stage = WorkflowStage(
        id="../migration plan",
        purpose="Review guarded patch plan",
        work_unit_ids=["patch-plan"],
        write_policy="guarded",
    )
    boundary = BoundaryResult(
        stage_id=stage.id,
        status="passed",
        checked_paths=["src/users.py"],
        contract_required=True,
        contract_found=True,
        declared_write_paths=[
            WritePathIntent(
                path="src/users.py",
                action="modify",
                reason="Rename User model to Account",
            )
        ],
        contract_checks=["python -m pytest tests/test_users.py"],
    )

    record = write_phase_draft_artifact(tmp_path, state, stage, boundary)

    assert record is not None
    assert record.name == WRITE_PHASE_DRAFT_ARTIFACT_NAME
    assert record.stage_id == stage.id
    assert record.path == "artifacts/migration-plan/write-phase-draft.md"
    assert state.artifacts == [record]
    content = read_artifact(
        tmp_path,
        state,
        WRITE_PHASE_DRAFT_ARTIFACT_NAME,
        stage_id=stage.id,
    )
    assert "# write phase draft" in content
    assert "Stage: ../migration plan" in content
    assert "Contract required: true" in content
    assert "Contract found: true" in content
    assert "src/users.py" in content
    assert "modify" in content
    assert "Rename User model to Account" in content
    assert "python -m pytest tests/test_users.py" in content
    assert "does not apply patches" in content


def test_write_phase_draft_is_idempotent(tmp_path):
    state = create_run_state(build_plan("migrate", "Rename User model to Account"))
    stage = WorkflowStage(
        id="migration-plan-review",
        purpose="Review guarded patch plan",
        work_unit_ids=["patch-plan"],
        write_policy="guarded",
    )
    boundary = BoundaryResult(
        stage_id=stage.id,
        status="passed",
        checked_paths=["src/users.py"],
        contract_found=True,
        declared_write_paths=[WritePathIntent(path="src/users.py")],
    )

    first = write_phase_draft_artifact(tmp_path, state, stage, boundary)
    second = write_phase_draft_artifact(tmp_path, state, stage, boundary)

    assert first == second
    assert len(state.artifacts) == 1


def test_write_phase_draft_skips_failed_boundary(tmp_path):
    state = create_run_state(build_plan("migrate", "Rename User model to Account"))
    stage = WorkflowStage(
        id="migration-plan-review",
        purpose="Review guarded patch plan",
        work_unit_ids=["patch-plan"],
        write_policy="guarded",
    )
    boundary = BoundaryResult(
        stage_id=stage.id,
        status="failed",
        checked_paths=["secrets/key.py"],
        contract_found=True,
        declared_write_paths=[WritePathIntent(path="secrets/key.py")],
    )

    record = write_phase_draft_artifact(tmp_path, state, stage, boundary)

    assert record is None
    assert state.artifacts == []


def test_write_phase_draft_skips_legacy_write_paths_without_contract(tmp_path):
    state = create_run_state(build_plan("migrate", "Rename User model to Account"))
    stage = WorkflowStage(
        id="migration-plan-review",
        purpose="Review guarded patch plan",
        work_unit_ids=["patch-plan"],
        write_policy="guarded",
    )
    boundary = BoundaryResult(
        stage_id=stage.id,
        status="passed",
        checked_paths=["src/users.py"],
        contract_required=False,
        contract_found=False,
    )

    record = write_phase_draft_artifact(tmp_path, state, stage, boundary)

    assert record is None
    assert state.artifacts == []
