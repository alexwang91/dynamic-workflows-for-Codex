from cdw.planner import build_plan
from cdw.workflow_spec import (
    load_workflow_spec,
    load_workflow_spec_bundle,
    save_workflow_spec,
)
from pydantic import ValidationError


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
    assert bundle.procedure is not None
    assert bundle.procedure.mode == "guarded"
    assert [stage.id for stage in bundle.procedure.stages] == [
        "migration-inventory",
        "migration-plan-review",
    ]
    assert bundle.procedure.stages[1].gate == "manual_review"
    assert bundle.procedure.stages[1].on_failure == "require_human"


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
