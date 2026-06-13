from pydantic import ValidationError

from cdw.planner import build_plan
from cdw.schemas import (
    WorkflowProcedure,
    WorkflowSpecBundle,
    WorkflowSpecConstraints,
    WorkflowSpecMetadata,
    WorkflowStage,
)
from cdw.workflow_spec import (
    load_workflow_spec,
    load_workflow_spec_bundle,
    save_workflow_spec,
)


def test_workflow_spec_round_trip(tmp_path):
    plan = build_plan("review", "Review branch")
    path = tmp_path / "review.workflow.json"

    save_workflow_spec(path, plan)
    loaded = load_workflow_spec(path)

    assert loaded == plan
    assert loaded.schema_version == "1"


def test_workflow_spec_saves_v3_envelope(tmp_path):
    plan = build_plan("migrate", "Rename User model to Account")
    path = tmp_path / "migrate.workflow.json"

    save_workflow_spec(path, plan)
    bundle = load_workflow_spec_bundle(path)

    assert bundle.schema_version == "3"
    assert bundle.kind == "codex.dynamic-workflow"
    assert bundle.plan == plan
    assert bundle.constraints.write_policy == "write-heavy"
    assert bundle.constraints.requires_human_approval is True
    assert ".cdw/**" in bundle.constraints.forbidden_paths
    assert ".env*" in bundle.constraints.forbidden_paths
    assert bundle.procedure is not None
    assert bundle.procedure.mode == "guarded"
    assert [stage.id for stage in bundle.procedure.stages] == [
        "migration-inventory",
        "migration-plan-review",
    ]
    assert bundle.procedure.stages[1].gate == "manual_review"
    assert bundle.procedure.stages[1].on_failure == "require_human"
    assert bundle.procedure.stages[0].produces == ["migration inventory"]
    assert bundle.procedure.stages[1].depends_on == ["migration-inventory"]
    assert bundle.procedure.stages[1].consumes == ["migration inventory"]
    assert bundle.procedure.stages[1].produces == [
        "guarded patch plan",
        "migration risk review",
    ]
    assert bundle.procedure.stages[1].write_policy == "guarded"


def test_workflow_spec_saves_v3_procedure_graph(tmp_path):
    plan = build_plan("review", "Review branch")
    path = tmp_path / "review.workflow.json"

    save_workflow_spec(path, plan)
    bundle = load_workflow_spec_bundle(path)

    assert bundle.schema_version == "3"
    assert bundle.procedure is not None
    assert bundle.procedure.mode == "fan-out"
    assert bundle.procedure.triggers == ["review"]
    assert bundle.procedure.stages[0].id == "review-workers"
    assert bundle.procedure.stages[0].work_unit_ids == [
        work_unit.id for work_unit in plan.work_units
    ]
    assert bundle.procedure.stages[0].gate == "all_required_verified"
    assert bundle.procedure.stages[0].on_failure == "stop"
    assert bundle.procedure.stages[0].depends_on == []
    assert bundle.procedure.stages[0].consumes == []
    assert bundle.procedure.stages[0].produces == ["synthesis report"]
    assert bundle.procedure.stages[0].write_policy == "read-only"


def test_workflow_spec_rejects_unknown_stage_dependency():
    plan = build_plan("review", "Review branch")

    try:
        _bundle_with_stages(
            plan,
            [
                WorkflowStage(
                    id="review-workers",
                    purpose="Review the branch",
                    work_unit_ids=[work_unit.id for work_unit in plan.work_units],
                    depends_on=["missing-stage"],
                )
            ],
        )
    except ValidationError as exc:
        assert "unknown stage dependency ids" in str(exc)
    else:
        raise AssertionError("expected unknown stage dependency to fail")


def test_workflow_spec_rejects_self_stage_dependency():
    plan = build_plan("review", "Review branch")

    try:
        _bundle_with_stages(
            plan,
            [
                WorkflowStage(
                    id="review-workers",
                    purpose="Review the branch",
                    work_unit_ids=[work_unit.id for work_unit in plan.work_units],
                    depends_on=["review-workers"],
                )
            ],
        )
    except ValidationError as exc:
        assert "stage cannot depend on itself" in str(exc)
    else:
        raise AssertionError("expected self stage dependency to fail")


def test_workflow_spec_rejects_out_of_order_stage_dependency():
    plan = build_plan("review", "Review branch")

    try:
        _bundle_with_stages(
            plan,
            [
                WorkflowStage(
                    id="second",
                    purpose="Second stage",
                    work_unit_ids=["security"],
                    depends_on=["first"],
                ),
                WorkflowStage(
                    id="first",
                    purpose="First stage",
                    work_unit_ids=["tests", "compatibility", "maintainability"],
                ),
            ],
        )
    except ValidationError as exc:
        assert "stage dependencies must reference earlier stages" in str(exc)
    else:
        raise AssertionError("expected out-of-order stage dependency to fail")


def test_workflow_spec_rejects_duplicate_stage_ids():
    plan = build_plan("review", "Review branch")

    try:
        _bundle_with_stages(
            plan,
            [
                WorkflowStage(
                    id="review",
                    purpose="First review stage",
                    work_unit_ids=["security"],
                ),
                WorkflowStage(
                    id="review",
                    purpose="Second review stage",
                    work_unit_ids=["tests", "compatibility", "maintainability"],
                ),
            ],
        )
    except ValidationError as exc:
        assert "duplicate stage ids" in str(exc)
    else:
        raise AssertionError("expected duplicate stage id to fail")


def test_workflow_spec_rejects_consumed_artifact_without_dependency():
    plan = build_plan("review", "Review branch")

    try:
        _bundle_with_stages(
            plan,
            [
                WorkflowStage(
                    id="context",
                    purpose="Context",
                    work_unit_ids=["security"],
                    produces=["scope summary"],
                ),
                WorkflowStage(
                    id="review",
                    purpose="Review",
                    work_unit_ids=["tests", "compatibility", "maintainability"],
                    consumes=["scope summary"],
                ),
            ],
        )
    except ValidationError as exc:
        assert "consumed artifacts must be produced by declared dependencies" in str(
            exc
        )
    else:
        raise AssertionError("expected undeclared artifact dependency to fail")


def test_workflow_spec_rejects_guarded_stage_without_human_gate():
    plan = build_plan("review", "Review branch")

    try:
        _bundle_with_stages(
            plan,
            [
                WorkflowStage(
                    id="guarded-review",
                    purpose="Guarded review",
                    work_unit_ids=[work_unit.id for work_unit in plan.work_units],
                    write_policy="guarded",
                )
            ],
        )
    except ValidationError as exc:
        assert "guarded stages require human approval gates" in str(exc)
    else:
        raise AssertionError("expected guarded stage without human gate to fail")


def test_workflow_spec_rejects_write_heavy_stage_without_artifact_boundary():
    plan = build_plan("review", "Review branch")

    try:
        _bundle_with_stages(
            plan,
            [
                WorkflowStage(
                    id="write-heavy-review",
                    purpose="Write-heavy review",
                    work_unit_ids=[work_unit.id for work_unit in plan.work_units],
                    gate="manual_review",
                    on_failure="require_human",
                    write_policy="write-heavy",
                )
            ],
        )
    except ValidationError as exc:
        assert "write-heavy stages require dependencies and consumed artifacts" in str(
            exc
        )
    else:
        raise AssertionError("expected write-heavy stage without boundary to fail")


def test_workflow_spec_rejects_write_heavy_without_human_approval():
    plan = build_plan("migrate", "Rename User model to Account")

    try:
        _bundle_with_stages(
            plan,
            [
                WorkflowStage(
                    id="migration-inventory",
                    purpose="Inventory",
                    work_unit_ids=["inventory"],
                    produces=["migration inventory"],
                ),
                WorkflowStage(
                    id="migration-plan-review",
                    purpose="Plan",
                    work_unit_ids=["patch-plan", "verification"],
                    depends_on=["migration-inventory"],
                    consumes=["migration inventory"],
                    produces=["guarded patch plan"],
                    gate="manual_review",
                    on_failure="require_human",
                    write_policy="guarded",
                ),
            ],
            constraints=WorkflowSpecConstraints(
                write_policy="write-heavy",
                requires_human_approval=False,
            ),
        )
    except ValidationError as exc:
        assert "write-heavy specs require human approval" in str(exc)
    else:
        raise AssertionError("expected write-heavy spec without approval to fail")


def test_load_workflow_spec_bundle_backfills_v2_procedure(tmp_path):
    plan = build_plan("debug", "Debug flaky test")
    path = tmp_path / "debug-v2.workflow.json"
    path.write_text(
        (
            "{\n"
            '  "schema_version": "2",\n'
            '  "kind": "codex.dynamic-workflow",\n'
            '  "metadata": {"name": "debug", "description": "debug", "created_by": "cdw"},\n'
            '  "constraints": {"write_policy": "read-only", "allowed_paths": [], "forbidden_paths": [], "requires_human_approval": false},\n'
            '  "acceptance_criteria": ["supported_hypothesis_or_max_iterations"],\n'
            f'  "plan": {plan.model_dump_json()}\n'
            "}\n"
        ),
        encoding="utf-8",
    )

    bundle = load_workflow_spec_bundle(path)

    assert bundle.schema_version == "2"
    assert bundle.plan == plan
    assert bundle.procedure is not None
    assert bundle.procedure.mode == "fan-out"
    assert bundle.procedure.stages[0].work_unit_ids == [
        work_unit.id for work_unit in plan.work_units
    ]


def test_load_workflow_spec_bundle_rejects_unknown_stage_work_unit(tmp_path):
    plan = build_plan("review", "Review branch")
    path = tmp_path / "invalid.workflow.json"
    path.write_text(
        (
            "{\n"
            '  "schema_version": "3",\n'
            '  "kind": "codex.dynamic-workflow",\n'
            '  "metadata": {"name": "review", "description": "review", "created_by": "cdw"},\n'
            '  "constraints": {"write_policy": "read-only", "allowed_paths": [], "forbidden_paths": [], "requires_human_approval": false},\n'
            '  "acceptance_criteria": ["all_required_units_verified"],\n'
            '  "procedure": {\n'
            '    "mode": "fan-out",\n'
            '    "triggers": ["review"],\n'
            '    "stages": [\n'
            '      {"id": "review-workers", "purpose": "Review the branch", "work_unit_ids": ["missing-worker"], "gate": "all_required_verified", "on_failure": "stop"}\n'
            "    ],\n"
            '    "final_artifacts": ["synthesis report"]\n'
            "  },\n"
            f'  "plan": {plan.model_dump_json()}\n'
            "}\n"
        ),
        encoding="utf-8",
    )

    try:
        load_workflow_spec_bundle(path)
    except ValidationError as exc:
        assert "unknown work unit ids" in str(exc)
    else:
        raise AssertionError("expected invalid procedure reference to fail")


def test_load_workflow_spec_accepts_v1_plan_root(tmp_path):
    plan = build_plan("review", "Review branch")
    path = tmp_path / "review-v1.workflow.json"
    path.write_text(plan.model_dump_json(indent=2), encoding="utf-8")

    loaded = load_workflow_spec(path)

    assert loaded == plan


def _bundle_with_stages(
    plan,
    stages,
    constraints: WorkflowSpecConstraints | None = None,
) -> WorkflowSpecBundle:
    return WorkflowSpecBundle(
        schema_version="3",
        metadata=WorkflowSpecMetadata(name="test", description="test"),
        constraints=constraints or WorkflowSpecConstraints(),
        acceptance_criteria=[plan.stop_condition],
        procedure=WorkflowProcedure(
            mode="sequence",
            triggers=[plan.command.value],
            stages=stages,
            final_artifacts=["synthesis report"],
        ),
        plan=plan,
    )
