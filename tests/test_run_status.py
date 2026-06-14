import os

import pytest

from cdw.planner import build_plan
from cdw.run_status import list_run_summaries, summarize_run
from cdw.schemas import (
    ArtifactRecord,
    BoundaryResult,
    BoundaryViolation,
    SynthesisReport,
    VerificationResult,
    WorkerResult,
)
from cdw.state import create_run_state, run_dir, save_run_state


def test_summarize_run_reports_pending_human_approval(tmp_path):
    state = create_run_state(
        build_plan("migrate", "Rename User model to Account"),
        adapter="codex-cli",
    )
    state.pending_human_approval = "migration-plan-review"
    state.worker_results.append(
        WorkerResult(
            work_unit_id="inventory",
            status="succeeded",
            summary="Inventory complete",
        )
    )
    state.verification_results.append(
        VerificationResult(
            work_unit_id="inventory",
            status="passed",
            notes="Inventory verified",
        )
    )
    state.artifacts.append(
        ArtifactRecord(
            name="migration inventory",
            stage_id="migration-inventory",
            path="artifacts/migration-inventory/migration-inventory.md",
            source_work_unit_ids=["inventory"],
        )
    )
    state.boundary_results.append(
        BoundaryResult(
            stage_id="migration-plan-review",
            status="failed",
            checked_paths=["secrets/key.py"],
            contract_required=True,
            contract_found=False,
            violations=[
                BoundaryViolation(
                    path="secrets/key.py",
                    reason="forbidden",
                    pattern="secrets/**",
                )
            ],
        )
    )
    state.synthesis = SynthesisReport(
        status="waiting_for_human",
        summary="Waiting for approval",
        unresolved=["migration-plan-review"],
    )
    state_path = save_run_state(tmp_path, state)

    summary = summarize_run(tmp_path, state.run_id)

    assert summary.run_id == state.run_id
    assert summary.status == "waiting_for_human"
    assert summary.command == "migrate"
    assert summary.request == "Rename User model to Account"
    assert summary.adapter == "codex-cli"
    assert summary.pending_human_approval == "migration-plan-review"
    assert summary.worker_count == 1
    assert summary.verification_count == 1
    assert summary.artifact_count == 1
    assert summary.artifacts[0]["name"] == "migration inventory"
    assert summary.boundary_failure_count == 1
    assert summary.boundary_failures[0]["stage_id"] == "migration-plan-review"
    assert summary.boundary_failures[0]["contract_required"] is True
    assert summary.boundary_failures[0]["contract_found"] is False
    assert summary.state_path == str(state_path)
    assert summary.resume_command == (
        f"python -m cdw resume {state.run_id} --adapter codex-cli --approve-human-gates"
    )


def test_summarize_run_reports_missing_run(tmp_path):
    with pytest.raises(RuntimeError, match="run not found: missing"):
        summarize_run(tmp_path, "missing")


def test_list_run_summaries_orders_newest_first(tmp_path):
    first = create_run_state(build_plan("review", "Review branch"))
    second = create_run_state(build_plan("debug", "Debug branch"))
    first_path = save_run_state(tmp_path, first)
    second_path = save_run_state(tmp_path, second)
    os.utime(first_path, (100, 100))
    os.utime(second_path, (200, 200))

    summaries = list_run_summaries(tmp_path)

    assert [summary.run_id for summary in summaries] == [second.run_id, first.run_id]


def test_list_run_summaries_returns_empty_when_runs_dir_is_missing(tmp_path):
    assert list_run_summaries(tmp_path) == []


def test_list_run_summaries_skips_corrupt_state(tmp_path):
    good = create_run_state(build_plan("review", "Review branch"))
    save_run_state(tmp_path, good)
    corrupt_dir = run_dir(tmp_path, "corrupt")
    corrupt_dir.mkdir(parents=True)
    (corrupt_dir / "state.json").write_text("{bad json", encoding="utf-8")

    summaries = list_run_summaries(tmp_path)

    assert [summary.run_id for summary in summaries] == [good.run_id]
