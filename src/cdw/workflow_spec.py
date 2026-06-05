from __future__ import annotations

import json
from pathlib import Path

from cdw.schemas import (
    WorkflowPlan,
    WorkflowSpecBundle,
    WorkflowSpecConstraints,
    WorkflowSpecMetadata,
)


def save_workflow_spec(path: Path, plan: WorkflowPlan) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    bundle = _bundle_for_plan(plan)
    path.write_text(bundle.model_dump_json(indent=2), encoding="utf-8")
    return path


def load_workflow_spec(path: Path) -> WorkflowPlan:
    return load_workflow_spec_bundle(path).plan


def load_workflow_spec_bundle(path: Path) -> WorkflowSpecBundle:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("kind") == "codex.dynamic-workflow":
        return WorkflowSpecBundle.model_validate(data)
    plan = WorkflowPlan.model_validate(data)
    return _bundle_for_plan(plan)


def _bundle_for_plan(plan: WorkflowPlan) -> WorkflowSpecBundle:
    return WorkflowSpecBundle(
        metadata=WorkflowSpecMetadata(
            name=f"{plan.command.value}: {plan.request}",
            description=plan.request,
        ),
        constraints=_constraints_for_plan(plan),
        acceptance_criteria=[plan.stop_condition],
        plan=plan,
    )


def _constraints_for_plan(plan: WorkflowPlan) -> WorkflowSpecConstraints:
    if plan.command == "migrate":
        return WorkflowSpecConstraints(
            write_policy="write-heavy",
            requires_human_approval=True,
        )
    return WorkflowSpecConstraints(write_policy="read-only")
