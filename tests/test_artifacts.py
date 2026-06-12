import pytest

from cdw.artifacts import (
    artifact_file_name,
    consumed_artifact_context,
    read_artifact,
    write_stage_artifacts,
)
from cdw.planner import build_plan
from cdw.schemas import ArtifactRecord, WorkerResult, WorkflowStage
from cdw.state import create_run_state


def test_artifact_file_name_slugifies_names():
    assert artifact_file_name("Migration Inventory!") == "migration-inventory.md"
    assert artifact_file_name("   Risk   Review   ") == "risk-review.md"


def test_write_stage_artifacts_persists_markdown_and_updates_index(tmp_path):
    state = create_run_state(build_plan("review", "Review branch"))
    stage = WorkflowStage(
        id="stage-one",
        purpose="Produce first artifact",
        work_unit_ids=["security"],
        produces=["Scope Summary"],
    )
    state.worker_results.append(
        WorkerResult(
            work_unit_id="security",
            status="succeeded",
            summary="Security review complete",
            evidence=["No auth regression found."],
            raw_output="raw security output",
        )
    )

    records = write_stage_artifacts(tmp_path, state, stage)

    assert len(records) == 1
    assert state.artifacts == records
    assert records[0].path == "artifacts/stage-one/scope-summary.md"
    artifact_path = tmp_path / ".cdw" / "runs" / state.run_id / records[0].path
    content = artifact_path.read_text(encoding="utf-8")
    assert "# Scope Summary" in content
    assert "Security review complete" in content
    assert "No auth regression found." in content


def test_write_stage_artifacts_is_idempotent(tmp_path):
    state = create_run_state(build_plan("review", "Review branch"))
    stage = WorkflowStage(
        id="stage-one",
        purpose="Produce first artifact",
        work_unit_ids=["security"],
        produces=["Scope Summary"],
    )
    state.worker_results.append(
        WorkerResult(
            work_unit_id="security",
            status="succeeded",
            summary="Security review complete",
        )
    )

    write_stage_artifacts(tmp_path, state, stage)
    write_stage_artifacts(tmp_path, state, stage)

    assert len(state.artifacts) == 1


def test_write_stage_artifacts_sanitizes_stage_directory(tmp_path):
    state = create_run_state(build_plan("review", "Review branch"))
    stage = WorkflowStage(
        id="../escape",
        purpose="Produce first artifact",
        work_unit_ids=["security"],
        produces=["Risky"],
    )
    state.worker_results.append(
        WorkerResult(
            work_unit_id="security",
            status="succeeded",
            summary="Security review complete",
        )
    )

    records = write_stage_artifacts(tmp_path, state, stage)

    assert records[0].path == "artifacts/escape/risky.md"


def test_read_artifact_rejects_ambiguous_name_without_stage(tmp_path):
    state = create_run_state(build_plan("review", "Review branch"))
    run_path = tmp_path / ".cdw" / "runs" / state.run_id
    first_path = run_path / "artifacts" / "first" / "notes.md"
    second_path = run_path / "artifacts" / "second" / "notes.md"
    first_path.parent.mkdir(parents=True)
    second_path.parent.mkdir(parents=True)
    first_path.write_text("first notes", encoding="utf-8")
    second_path.write_text("second notes", encoding="utf-8")
    state.artifacts.extend(
        [
            ArtifactRecord(
                name="notes",
                stage_id="first",
                path="artifacts/first/notes.md",
                source_work_unit_ids=["security"],
            ),
            ArtifactRecord(
                name="notes",
                stage_id="second",
                path="artifacts/second/notes.md",
                source_work_unit_ids=["tests"],
            ),
        ]
    )

    with pytest.raises(RuntimeError, match="ambiguous artifact"):
        read_artifact(tmp_path, state, "notes")

    assert read_artifact(tmp_path, state, "notes", stage_id="second") == "second notes"


def test_read_artifact_rejects_paths_outside_run_dir(tmp_path):
    state = create_run_state(build_plan("review", "Review branch"))
    state.artifacts.append(
        ArtifactRecord(
            name="bad",
            stage_id="stage-one",
            path="../bad.md",
            source_work_unit_ids=["security"],
        )
    )

    with pytest.raises(RuntimeError, match="artifact path escapes run directory"):
        read_artifact(tmp_path, state, "bad")


def test_consumed_artifact_context_formats_declared_inputs(tmp_path):
    state = create_run_state(build_plan("review", "Review branch"))
    stage = WorkflowStage(
        id="review",
        purpose="Review",
        work_unit_ids=["tests"],
        depends_on=["context"],
        consumes=["scope summary"],
    )
    artifact_path = tmp_path / ".cdw" / "runs" / state.run_id / "artifacts" / "context"
    artifact_path.mkdir(parents=True)
    (artifact_path / "scope-summary.md").write_text(
        "Scoped auth context",
        encoding="utf-8",
    )
    state.artifacts.append(
        ArtifactRecord(
            name="scope summary",
            stage_id="context",
            path="artifacts/context/scope-summary.md",
            source_work_unit_ids=["security"],
        )
    )

    context = consumed_artifact_context(tmp_path, state, stage)

    assert "Consumed artifacts" in context
    assert "scope summary" in context
    assert "Scoped auth context" in context
