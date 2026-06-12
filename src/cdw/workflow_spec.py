from __future__ import annotations

import json
from pathlib import Path

from cdw.schemas import (
    WorkflowProcedure,
    WorkflowPlan,
    WorkflowSpecBundle,
    WorkflowSpecConstraints,
    WorkflowSpecMetadata,
    WorkflowStage,
)


def save_workflow_spec(path: Path, plan: WorkflowPlan) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    bundle = build_workflow_spec_bundle(plan)
    return save_workflow_spec_bundle(path, bundle)


def save_workflow_spec_bundle(path: Path, bundle: WorkflowSpecBundle) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(bundle.model_dump_json(indent=2), encoding="utf-8")
    return path


def load_workflow_spec(path: Path) -> WorkflowPlan:
    return load_workflow_spec_bundle(path).plan


def load_workflow_spec_bundle(path: Path) -> WorkflowSpecBundle:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("kind") == "codex.dynamic-workflow":
        bundle = WorkflowSpecBundle.model_validate(data)
        return _with_default_procedure(bundle)
    plan = WorkflowPlan.model_validate(data)
    return build_workflow_spec_bundle(plan)


def build_workflow_spec_bundle(plan: WorkflowPlan) -> WorkflowSpecBundle:
    return WorkflowSpecBundle(
        schema_version="3",
        metadata=WorkflowSpecMetadata(
            name=f"{plan.command.value}: {plan.request}",
            description=plan.request,
        ),
        constraints=_constraints_for_plan(plan),
        acceptance_criteria=[plan.stop_condition],
        procedure=_procedure_for_plan(plan),
        plan=plan,
    )


def _constraints_for_plan(plan: WorkflowPlan) -> WorkflowSpecConstraints:
    if plan.command == "migrate":
        return WorkflowSpecConstraints(
            write_policy="write-heavy",
            requires_human_approval=True,
        )
    return WorkflowSpecConstraints(write_policy="read-only")


def _with_default_procedure(bundle: WorkflowSpecBundle) -> WorkflowSpecBundle:
    if bundle.procedure is not None:
        return bundle
    return bundle.model_copy(update={"procedure": _procedure_for_plan(bundle.plan)})


def _procedure_for_plan(plan: WorkflowPlan) -> WorkflowProcedure:
    if plan.command == "migrate":
        return _migration_procedure(plan)
    return WorkflowProcedure(
        mode=_procedure_mode_for_plan(plan),
        triggers=[plan.command.value],
        stages=[
            WorkflowStage(
                id=_default_stage_id(plan),
                purpose=f"Run {plan.command.value} workflow workers",
                work_unit_ids=[work_unit.id for work_unit in plan.work_units],
                produces=["synthesis report"],
                gate="all_required_verified",
                on_failure="stop",
            )
        ],
        final_artifacts=["synthesis report"],
    )


def _migration_procedure(plan: WorkflowPlan) -> WorkflowProcedure:
    work_unit_ids = [work_unit.id for work_unit in plan.work_units]
    stages = []
    if "inventory" in work_unit_ids:
        stages.append(
            WorkflowStage(
                id="migration-inventory",
                purpose="Build a read-only inventory before write-heavy planning",
                work_unit_ids=["inventory"],
                produces=["migration inventory"],
                gate="all_required_verified",
                on_failure="stop",
                write_policy="read-only",
            )
        )
    remaining_ids = [
        work_unit_id for work_unit_id in work_unit_ids if work_unit_id != "inventory"
    ]
    if remaining_ids:
        stages.append(
            WorkflowStage(
                id="migration-plan-review",
                purpose="Plan and challenge guarded migration slices",
                work_unit_ids=remaining_ids,
                depends_on=["migration-inventory"] if "inventory" in work_unit_ids else [],
                consumes=["migration inventory"] if "inventory" in work_unit_ids else [],
                produces=["guarded patch plan", "migration risk review"],
                gate="manual_review",
                on_failure="require_human",
                write_policy="guarded",
            )
        )
    return WorkflowProcedure(
        mode="guarded",
        triggers=["migrate", "migration"],
        stages=stages,
        final_artifacts=["migration inventory", "guarded patch plan", "synthesis report"],
    )


def _procedure_mode_for_plan(plan: WorkflowPlan) -> str:
    if plan.command == "plan":
        return "single-stage"
    return "fan-out"


def _default_stage_id(plan: WorkflowPlan) -> str:
    if plan.command == "review":
        return "review-workers"
    if plan.command == "debug":
        return "hypothesis-investigators"
    if plan.command == "plan":
        return "workflow-planner"
    return f"{plan.command.value}-workers"
