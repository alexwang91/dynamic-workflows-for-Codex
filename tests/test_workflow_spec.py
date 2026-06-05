from cdw.planner import build_plan
from cdw.workflow_spec import load_workflow_spec, save_workflow_spec


def test_workflow_spec_round_trip(tmp_path):
    plan = build_plan("review", "Review branch")
    path = tmp_path / "review.workflow.json"

    save_workflow_spec(path, plan)
    loaded = load_workflow_spec(path)

    assert loaded == plan
    assert loaded.schema_version == "1"
