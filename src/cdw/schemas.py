from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Command(str, Enum):
    PLAN = "plan"
    REVIEW = "review"
    DEBUG = "debug"
    MIGRATE = "migrate"


class WorkUnit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    role: str = Field(min_length=1)
    goal: str = Field(min_length=1)
    prompt: str = Field(min_length=1)
    expected_output: str = Field(min_length=1)
    required: bool = True


class WorkflowPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "1"
    command: Command
    request: str = Field(min_length=1)
    pattern: str = Field(min_length=1)
    work_units: list[WorkUnit] = Field(min_length=1)
    verification_strategy: str = Field(min_length=1)
    stop_condition: str = Field(min_length=1)
    max_iterations: int = Field(default=1, ge=1, le=10)


class WorkflowSpecMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(default="Untitled workflow", min_length=1)
    description: str = ""
    created_by: str = Field(default="cdw", min_length=1)


class WorkflowSpecConstraints(BaseModel):
    model_config = ConfigDict(extra="forbid")

    write_policy: Literal["read-only", "guarded", "write-heavy"] = "read-only"
    allowed_paths: list[str] = Field(default_factory=list)
    forbidden_paths: list[str] = Field(default_factory=list)
    requires_human_approval: bool = False


StageGate = Literal["all_required_verified", "any_verified", "manual_review"]
FailureBehavior = Literal["stop", "continue", "require_human"]
ProcedureMode = Literal["single-stage", "fan-out", "sequence", "guarded"]
StageWritePolicy = Literal["read-only", "guarded", "write-heavy"]


class WorkflowStage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    purpose: str = Field(min_length=1)
    work_unit_ids: list[str] = Field(min_length=1)
    depends_on: list[str] = Field(default_factory=list)
    consumes: list[str] = Field(default_factory=list)
    produces: list[str] = Field(default_factory=list)
    gate: StageGate = "all_required_verified"
    on_failure: FailureBehavior = "stop"
    write_policy: StageWritePolicy = "read-only"


class WorkflowProcedure(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: ProcedureMode
    triggers: list[str] = Field(default_factory=list)
    stages: list[WorkflowStage] = Field(min_length=1)
    final_artifacts: list[str] = Field(default_factory=list)


class WorkflowSpecBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["2", "3"] = "3"
    kind: Literal["codex.dynamic-workflow"] = "codex.dynamic-workflow"
    metadata: WorkflowSpecMetadata = Field(default_factory=WorkflowSpecMetadata)
    constraints: WorkflowSpecConstraints = Field(
        default_factory=WorkflowSpecConstraints
    )
    acceptance_criteria: list[str] = Field(default_factory=list)
    procedure: WorkflowProcedure | None = None
    plan: WorkflowPlan

    @model_validator(mode="after")
    def validate_procedure_references(self) -> "WorkflowSpecBundle":
        if self.procedure is None:
            return self

        stage_ids = [stage.id for stage in self.procedure.stages]
        duplicate_stage_ids = sorted(
            stage_id for stage_id in set(stage_ids) if stage_ids.count(stage_id) > 1
        )
        if duplicate_stage_ids:
            raise ValueError(f"duplicate stage ids: {duplicate_stage_ids}")

        known_ids = {work_unit.id for work_unit in self.plan.work_units}
        referenced_ids = []
        for stage in self.procedure.stages:
            unknown_ids = sorted(set(stage.work_unit_ids) - known_ids)
            if unknown_ids:
                raise ValueError(f"unknown work unit ids: {unknown_ids}")
            referenced_ids.extend(stage.work_unit_ids)

        duplicate_ids = sorted(
            work_unit_id
            for work_unit_id in set(referenced_ids)
            if referenced_ids.count(work_unit_id) > 1
        )
        if duplicate_ids:
            raise ValueError(f"duplicate staged work unit ids: {duplicate_ids}")

        missing_ids = sorted(known_ids - set(referenced_ids))
        if missing_ids:
            raise ValueError(f"unstaged work unit ids: {missing_ids}")

        all_stage_ids = set(stage_ids)
        seen_stage_ids: set[str] = set()
        produced_by: dict[str, set[str]] = {}
        for stage in self.procedure.stages:
            dependency_ids = set(stage.depends_on)
            if stage.id in dependency_ids:
                raise ValueError("stage cannot depend on itself")

            unknown_dependency_ids = sorted(dependency_ids - all_stage_ids)
            if unknown_dependency_ids:
                raise ValueError(
                    f"unknown stage dependency ids: {unknown_dependency_ids}"
                )

            out_of_order_dependency_ids = sorted(dependency_ids - seen_stage_ids)
            if out_of_order_dependency_ids:
                raise ValueError(
                    "stage dependencies must reference earlier stages: "
                    f"{out_of_order_dependency_ids}"
                )

            for artifact in stage.consumes:
                producer_stage_ids = produced_by.get(artifact, set())
                if not producer_stage_ids.intersection(dependency_ids):
                    raise ValueError(
                        "consumed artifacts must be produced by declared "
                        f"dependencies: {artifact}"
                    )

            if stage.write_policy in {"guarded", "write-heavy"} and not (
                stage.gate == "manual_review" or stage.on_failure == "require_human"
            ):
                raise ValueError("guarded stages require human approval gates")

            if stage.write_policy == "write-heavy" and (
                not stage.depends_on or not stage.consumes
            ):
                raise ValueError(
                    "write-heavy stages require dependencies and consumed artifacts"
                )

            for artifact in stage.produces:
                produced_by.setdefault(artifact, set()).add(stage.id)
            seen_stage_ids.add(stage.id)

        if self.constraints.write_policy == "write-heavy":
            if not self.constraints.requires_human_approval:
                raise ValueError("write-heavy specs require human approval")
            human_gated_stages = [
                stage
                for stage in self.procedure.stages
                if stage.gate == "manual_review"
                or stage.on_failure == "require_human"
            ]
            if not human_gated_stages:
                raise ValueError("write-heavy specs require a human-gated stage")

        return self


class WorkerStatus(str, Enum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class WorkerResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    work_unit_id: str = Field(min_length=1)
    status: WorkerStatus
    summary: str = Field(min_length=1)
    evidence: list[str] = Field(default_factory=list)
    raw_output: str = ""


class VerificationStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"


class VerificationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    work_unit_id: str = Field(min_length=1)
    status: VerificationStatus
    notes: str = Field(min_length=1)


class SynthesisReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["complete", "incomplete", "waiting_for_human"]
    summary: str = Field(min_length=1)
    findings: list[str] = Field(default_factory=list)
    unresolved: list[str] = Field(default_factory=list)


class ArtifactRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    stage_id: str = Field(min_length=1)
    path: str = Field(min_length=1)
    content_type: Literal["text/markdown"] = "text/markdown"
    source_work_unit_ids: list[str] = Field(default_factory=list)


class RunState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str = Field(min_length=1)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    plan: WorkflowPlan
    procedure: WorkflowProcedure | None = None
    worker_results: list[WorkerResult] = Field(default_factory=list)
    verification_results: list[VerificationResult] = Field(default_factory=list)
    artifacts: list[ArtifactRecord] = Field(default_factory=list)
    synthesis: SynthesisReport | None = None
    adapter: str | None = None
    pending_human_approval: str | None = None
