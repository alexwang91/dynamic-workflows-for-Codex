import pytest
from pydantic import ValidationError

from cdw.schemas import (
    WorkflowPlan,
    WorkflowProcedure,
    WorkflowSpecBundle,
    WorkflowStage,
    WorkUnit,
)


def test_workflow_plan_requires_work_units_and_stop_condition():
    plan = WorkflowPlan(
        command="review",
        request="Review branch",
        pattern="fan-out-and-synthesize",
        work_units=[
            WorkUnit(
                id="security",
                role="security reviewer",
                goal="Find security risks",
                prompt="Review security risks",
                expected_output="Findings with evidence",
            )
        ],
        verification_strategy="adversarial",
        stop_condition="all_required_units_verified",
    )

    assert plan.command == "review"
    assert plan.work_units[0].id == "security"


def test_workflow_plan_rejects_empty_work_units():
    with pytest.raises(ValidationError):
        WorkflowPlan(
            command="review",
            request="Review branch",
            pattern="fan-out-and-synthesize",
            work_units=[],
            verification_strategy="adversarial",
            stop_condition="all_required_units_verified",
        )


def test_workflow_spec_rejects_duplicate_staged_work_unit_ids():
    plan = _two_unit_review_plan()

    with pytest.raises(ValidationError, match="duplicate staged work unit ids"):
        WorkflowSpecBundle(
            procedure=WorkflowProcedure(
                mode="fan-out",
                stages=[
                    WorkflowStage(
                        id="first",
                        purpose="First pass",
                        work_unit_ids=["security"],
                    ),
                    WorkflowStage(
                        id="second",
                        purpose="Second pass",
                        work_unit_ids=["security", "tests"],
                    ),
                ],
            ),
            plan=plan,
        )


def test_workflow_spec_rejects_unstaged_work_unit_ids():
    plan = _two_unit_review_plan()

    with pytest.raises(ValidationError, match="unstaged work unit ids"):
        WorkflowSpecBundle(
            procedure=WorkflowProcedure(
                mode="fan-out",
                stages=[
                    WorkflowStage(
                        id="first",
                        purpose="First pass",
                        work_unit_ids=["security"],
                    )
                ],
            ),
            plan=plan,
        )


def _two_unit_review_plan() -> WorkflowPlan:
    return WorkflowPlan(
        command="review",
        request="Review branch",
        pattern="fan-out-and-synthesize",
        work_units=[
            WorkUnit(
                id="security",
                role="security reviewer",
                goal="Find security risks",
                prompt="Review security risks",
                expected_output="Findings with evidence",
            ),
            WorkUnit(
                id="tests",
                role="test reviewer",
                goal="Find test gaps",
                prompt="Review tests",
                expected_output="Test findings with evidence",
            ),
        ],
        verification_strategy="adversarial",
        stop_condition="all_required_units_verified",
    )
