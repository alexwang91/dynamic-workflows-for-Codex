import pytest
from pydantic import ValidationError

from cdw.schemas import WorkflowPlan, WorkUnit


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
