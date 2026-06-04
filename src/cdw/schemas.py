from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Command(str, Enum):
    PLAN = "plan"
    REVIEW = "review"
    DEBUG = "debug"


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

    status: Literal["complete", "incomplete"]
    summary: str = Field(min_length=1)
    findings: list[str] = Field(default_factory=list)
    unresolved: list[str] = Field(default_factory=list)


class RunState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str = Field(min_length=1)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    plan: WorkflowPlan
    worker_results: list[WorkerResult] = Field(default_factory=list)
    verification_results: list[VerificationResult] = Field(default_factory=list)
    synthesis: SynthesisReport | None = None
