from cdw.boundaries import check_stage_boundaries, extract_declared_write_paths
from cdw.schemas import WorkflowSpecConstraints, WorkflowStage, WorkerResult


def test_extract_declared_write_paths_from_explicit_section():
    output = """Summary

WRITE_PATHS:
- src/users.py
- `tests/test_users.py`

Notes after the path section.
"""

    assert extract_declared_write_paths(output) == [
        "src/users.py",
        "tests/test_users.py",
    ]


def test_extract_declared_write_paths_stops_before_plain_prose():
    output = """WRITE_PATHS:
src/users.py
This migration also needs a compatibility note.
"""

    assert extract_declared_write_paths(output) == ["src/users.py"]


def test_boundary_check_allows_declared_paths_inside_allowed_patterns():
    result = _worker_result("WRITE_PATHS:\n- src/users.py")
    stage = _guarded_stage()
    constraints = WorkflowSpecConstraints(
        allowed_paths=["src/**"],
        forbidden_paths=[".env*"],
    )

    boundary = check_stage_boundaries(constraints, stage, [result])

    assert boundary.status == "passed"
    assert boundary.checked_paths == ["src/users.py"]
    assert boundary.violations == []


def test_boundary_check_rejects_forbidden_paths_before_allowed_paths():
    result = _worker_result("WRITE_PATHS:\n- src/secrets/key.py")
    stage = _guarded_stage()
    constraints = WorkflowSpecConstraints(
        allowed_paths=["src/**"],
        forbidden_paths=["src/secrets/**"],
    )

    boundary = check_stage_boundaries(constraints, stage, [result])

    assert boundary.status == "failed"
    assert boundary.violations[0].path == "src/secrets/key.py"
    assert boundary.violations[0].reason == "forbidden"
    assert boundary.violations[0].pattern == "src/secrets/**"


def test_boundary_check_rejects_paths_outside_allowed_patterns():
    result = _worker_result("WRITE_PATHS:\n- docs/plan.md")
    stage = _guarded_stage()
    constraints = WorkflowSpecConstraints(allowed_paths=["src/**"])

    boundary = check_stage_boundaries(constraints, stage, [result])

    assert boundary.status == "failed"
    assert boundary.violations[0].path == "docs/plan.md"
    assert boundary.violations[0].reason == "outside_allowed_paths"
    assert boundary.violations[0].pattern == "src/**"


def test_boundary_check_rejects_absolute_and_parent_paths():
    result = _worker_result("WRITE_PATHS:\n- C:/secret.txt\n- ../escape.py")
    stage = _guarded_stage()
    constraints = WorkflowSpecConstraints(allowed_paths=["**"])

    boundary = check_stage_boundaries(constraints, stage, [result])

    assert boundary.status == "failed"
    assert [violation.reason for violation in boundary.violations] == [
        "invalid_path",
        "invalid_path",
    ]


def _guarded_stage() -> WorkflowStage:
    return WorkflowStage(
        id="guarded",
        purpose="Guarded patch planning",
        work_unit_ids=["patch-plan"],
        gate="manual_review",
        on_failure="require_human",
        write_policy="guarded",
    )


def _worker_result(output: str) -> WorkerResult:
    return WorkerResult(
        work_unit_id="patch-plan",
        status="succeeded",
        summary=output,
        evidence=[output],
        raw_output=output,
    )
