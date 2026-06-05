from cdw.planner import build_plan
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


def test_workflow_spec_saves_v2_envelope(tmp_path):
    plan = build_plan("migrate", "Rename User model to Account")
    path = tmp_path / "migrate.workflow.json"

    save_workflow_spec(path, plan)
    bundle = load_workflow_spec_bundle(path)

    assert bundle.schema_version == "2"
    assert bundle.kind == "codex.dynamic-workflow"
    assert bundle.plan == plan
    assert bundle.constraints.write_policy == "write-heavy"
    assert bundle.constraints.requires_human_approval is True


def test_load_workflow_spec_accepts_v1_plan_root(tmp_path):
    plan = build_plan("review", "Review branch")
    path = tmp_path / "review-v1.workflow.json"
    path.write_text(plan.model_dump_json(indent=2), encoding="utf-8")

    loaded = load_workflow_spec(path)

    assert loaded == plan
