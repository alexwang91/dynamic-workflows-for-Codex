from cdw.planner import build_plan
from cdw.state import create_run_state, load_run_state, save_run_state


def test_save_and_load_run_state(tmp_path):
    plan = build_plan("plan", "Review branch")
    state = create_run_state(plan)

    save_run_state(tmp_path, state)
    loaded = load_run_state(tmp_path, state.run_id)

    assert loaded.run_id == state.run_id
    assert loaded.plan.request == "Review branch"
