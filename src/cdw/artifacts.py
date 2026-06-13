from __future__ import annotations

import re
from pathlib import Path

from cdw.schemas import ArtifactRecord, RunState, WorkflowStage, WorkerResult
from cdw.state import run_dir


def artifact_file_name(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")
    return f"{slug or 'artifact'}.md"


def write_stage_artifacts(
    root: Path,
    state: RunState,
    stage: WorkflowStage,
) -> list[ArtifactRecord]:
    if not stage.produces:
        return []

    records = []
    stage_results = _stage_worker_results(state, stage)
    for artifact_name in stage.produces:
        existing = _find_record(state, artifact_name, stage_id=stage.id)
        record = existing or ArtifactRecord(
            name=artifact_name,
            stage_id=stage.id,
            path=_artifact_relative_path(stage.id, artifact_name),
            source_work_unit_ids=list(stage.work_unit_ids),
        )
        artifact_path = _artifact_path(root, state, record.path)
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_path.write_text(
            _render_artifact_markdown(artifact_name, stage, stage_results),
            encoding="utf-8",
        )
        if existing is None:
            state.artifacts.append(record)
        records.append(record)
    return records


def read_artifact(
    root: Path,
    state: RunState,
    name: str,
    stage_id: str | None = None,
) -> str:
    record = _select_record(state, name, stage_id=stage_id)
    return _artifact_path(root, state, record.path).read_text(encoding="utf-8")


def consumed_artifact_context(
    root: Path,
    state: RunState,
    stage: WorkflowStage,
) -> str:
    if not stage.consumes:
        return ""

    sections = ["## Consumed artifacts"]
    for artifact_name in stage.consumes:
        record = _select_consumed_record(state, artifact_name, stage.depends_on)
        content = _artifact_path(root, state, record.path).read_text(encoding="utf-8")
        sections.append(
            f"### {record.name} (from {record.stage_id})\n\n{content.strip()}"
        )
    return "\n\n".join(sections)


def artifact_summary_dicts(root: Path, state: RunState) -> list[dict[str, object]]:
    return [
        {
            "name": record.name,
            "stage_id": record.stage_id,
            "path": record.path,
            "absolute_path": str(_artifact_path(root, state, record.path)),
            "content_type": record.content_type,
            "source_work_unit_ids": list(record.source_work_unit_ids),
        }
        for record in state.artifacts
    ]


def _artifact_relative_path(stage_id: str, artifact_name: str) -> str:
    return f"artifacts/{_safe_path_segment(stage_id)}/{artifact_file_name(artifact_name)}"


def _artifact_path(root: Path, state: RunState, relative_path: str) -> Path:
    base_dir = run_dir(root, state.run_id).resolve()
    path = (base_dir / relative_path).resolve()
    if path != base_dir and base_dir not in path.parents:
        raise RuntimeError("artifact path escapes run directory")
    return path


def _safe_path_segment(value: str) -> str:
    segment = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    return segment or "stage"


def _find_record(
    state: RunState,
    name: str,
    stage_id: str,
) -> ArtifactRecord | None:
    for record in state.artifacts:
        if record.name == name and record.stage_id == stage_id:
            return record
    return None


def _select_record(
    state: RunState,
    name: str,
    stage_id: str | None = None,
) -> ArtifactRecord:
    records = [
        record
        for record in state.artifacts
        if record.name == name and (stage_id is None or record.stage_id == stage_id)
    ]
    if not records:
        qualifier = f" from stage {stage_id}" if stage_id else ""
        raise RuntimeError(f"artifact not found: {name}{qualifier}")
    if stage_id is None and len(records) > 1:
        stage_ids = ", ".join(record.stage_id for record in records)
        raise RuntimeError(f"ambiguous artifact: {name}; pass --stage-id ({stage_ids})")
    return records[0]


def _select_consumed_record(
    state: RunState,
    name: str,
    dependency_ids: list[str],
) -> ArtifactRecord:
    dependency_set = set(dependency_ids)
    records = [
        record
        for record in state.artifacts
        if record.name == name and record.stage_id in dependency_set
    ]
    if not records:
        raise RuntimeError(f"consumed artifact not found: {name}")
    if len(records) > 1:
        stage_ids = ", ".join(record.stage_id for record in records)
        raise RuntimeError(f"ambiguous consumed artifact: {name} ({stage_ids})")
    return records[0]


def _stage_worker_results(
    state: RunState,
    stage: WorkflowStage,
) -> list[WorkerResult]:
    stage_ids = set(stage.work_unit_ids)
    return [result for result in state.worker_results if result.work_unit_id in stage_ids]


def _render_artifact_markdown(
    artifact_name: str,
    stage: WorkflowStage,
    results: list[WorkerResult],
) -> str:
    lines = [
        f"# {artifact_name}",
        "",
        f"Stage: {stage.id}",
        f"Purpose: {stage.purpose}",
        "",
        "## Source work units",
    ]
    for result in results:
        lines.extend(
            [
                "",
                f"### {result.work_unit_id}",
                "",
                f"Status: {result.status.value}",
                "",
                result.summary,
            ]
        )
        if result.evidence:
            lines.extend(["", "Evidence:"])
            lines.extend(f"- {item}" for item in result.evidence)
        if result.raw_output:
            lines.extend(["", "Raw output:", "", result.raw_output])
    lines.append("")
    return "\n".join(lines)
