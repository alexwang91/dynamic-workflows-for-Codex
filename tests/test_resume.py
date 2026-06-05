from cdw.codex_mcp import FakeCodexAdapter
from cdw.planner import build_plan
from cdw.resume import resume_run
from cdw.runtime import execute_plan
from cdw.state import load_run_state, save_run_state


def test_resume_fills_missing_verifier_without_rerunning_workers(tmp_path):
    plan = build_plan("review", "Review branch")
    state = execute_plan(plan, tmp_path, FakeCodexAdapter())
    state.verification_results = state.verification_results[:2]
    state.synthesis = None
    save_run_state(tmp_path, state)

    resumed = resume_run(tmp_path, state.run_id, FakeCodexAdapter())

    loaded = load_run_state(tmp_path, state.run_id)
    assert resumed.run_id == state.run_id
    assert len(resumed.worker_results) == len(plan.work_units)
    assert len(resumed.verification_results) == len(plan.work_units)
    assert loaded.synthesis is not None
