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


class WorkflowStage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    purpose: str = Field(min_length=1)
    work_unit_ids: list[str] = Field(min_length=1)
    gate: StageGate = "all_required_verified"
    on_failure: FailureBehavior = "stop"


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


class RunState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str = Field(min_length=1)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    plan: WorkflowPlan
    procedure: WorkflowProcedure | None = None
    worker_results: list[WorkerResult] = Field(default_factory=list)
    verification_results: list[VerificationResult] = Field(default_factory=list)
    synthesis: SynthesisReport | None = None
    pending_human_approval: str | None = None
