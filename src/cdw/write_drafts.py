from __future__ import annotations

from pathlib import Path

from cdw.artifacts import write_artifact_content
from cdw.schemas import ArtifactRecord, BoundaryResult, RunState, WorkflowStage


WRITE_PHASE_DRAFT_ARTIFACT_NAME = "write phase draft"


def write_phase_draft_artifact(
    root: Path,
    state: RunState,
    stage: WorkflowStage,
    boundary_result: BoundaryResult,
) -> ArtifactRecord | None:
    if not _should_write_draft(stage, boundary_result):
        return None
    return write_artifact_content(
        root,
        state,
        WRITE_PHASE_DRAFT_ARTIFACT_NAME,
        stage,
        _render_write_phase_draft(stage, boundary_result),
    )


def _should_write_draft(
    stage: WorkflowStage,
    boundary_result: BoundaryResult,
) -> bool:
    return (
        stage.write_policy in {"guarded", "write-heavy"}
        and boundary_result.stage_id == stage.id
        and boundary_result.status == "passed"
        and boundary_result.contract_found
        and bool(boundary_result.declared_write_paths)
    )


def _render_write_phase_draft(
    stage: WorkflowStage,
    boundary_result: BoundaryResult,
) -> str:
    lines = [
        "# write phase draft",
        "",
        f"Stage: {stage.id}",
        f"Purpose: {stage.purpose}",
        "",
        "## Contract",
        "",
        f"Contract required: {_bool_text(boundary_result.contract_required)}",
        f"Contract found: {_bool_text(boundary_result.contract_found)}",
        "",
        "## Planned writes",
        "",
        "| Path | Action | Reason |",
        "| --- | --- | --- |",
    ]
    for intent in boundary_result.declared_write_paths:
        lines.append(
            "| "
            f"{_table_cell(intent.path)} | "
            f"{_table_cell(intent.action)} | "
            f"{_table_cell(intent.reason or 'not specified')} |"
        )

    lines.extend(["", "## Planned checks", ""])
    if boundary_result.contract_checks:
        lines.extend(f"- {check}" for check in boundary_result.contract_checks)
    else:
        lines.append("- No checks declared in WRITE_CONTRACT.")

    lines.extend(
        [
            "",
            "## Next step",
            "",
            (
                "Review this draft before any write-heavy execution. This artifact "
                "does not apply patches or modify source files."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def _bool_text(value: bool) -> str:
    return "true" if value else "false"


def _table_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()
