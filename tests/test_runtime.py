from cdw.codex_mcp import FakeCodexAdapter
from cdw.planner import build_plan
from cdw.runtime import execute_plan


def test_runtime_verifies_before_synthesis(tmp_path):
    plan = build_plan("review", "Review this branch")
    adapter = FakeCodexAdapter()

    state = execute_plan(plan, tmp_path, adapter)

    assert len(state.worker_results) == len(plan.work_units)
    assert len(state.verification_results) == len(plan.work_units)
    assert state.synthesis is not None
    assert state.synthesis.status == "complete"
    assert all(result.status == "passed" for result in state.verification_results)


def test_runtime_marks_incomplete_when_required_worker_fails(tmp_path):
    plan = build_plan("review", "Review this branch")
    adapter = FakeCodexAdapter(fail_work_unit_ids={"security"})

    state = execute_plan(plan, tmp_path, adapter)

    assert state.synthesis is not None
    assert state.synthesis.status == "incomplete"
    assert "security" in state.synthesis.unresolved
