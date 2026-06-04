from cdw.planner import build_plan
from cdw.state import create_run_state, load_run_state, save_run_state


def test_save_and_load_run_state(tmp_path):
    plan = build_plan("plan", "Review branch")
    state = create_run_state(plan)

    save_run_state(tmp_path, state)
    loaded = load_run_state(tmp_path, state.run_id)

    assert loaded.run_id == state.run_id
    assert loaded.plan.request == "Review branch"


def test_save_run_state_retries_transient_replace_permission_error(
    tmp_path, monkeypatch
):
    plan = build_plan("plan", "Review branch")
    state = create_run_state(plan)
    real_replace = __import__("os").replace
    calls = {"count": 0}

    def flaky_replace(src, dst):
        calls["count"] += 1
        if calls["count"] == 1:
            raise PermissionError("simulated transient lock")
        return real_replace(src, dst)

    monkeypatch.setattr("os.replace", flaky_replace)

    path = save_run_state(tmp_path, state)

    assert path.exists()
    assert calls["count"] == 2
