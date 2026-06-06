import subprocess

import pytest

from cdw.codex_cli import CodexCliAdapter
from cdw.schemas import WorkerResult, WorkerStatus, WorkUnit


def test_codex_cli_adapter_runs_worker_with_codex_exec(monkeypatch, tmp_path):
    calls = {}

    def fake_run(args, **kwargs):
        calls["args"] = args
        calls["kwargs"] = kwargs
        return subprocess.CompletedProcess(args, 0, stdout="worker output", stderr="")

    monkeypatch.setattr("subprocess.run", fake_run)
    adapter = CodexCliAdapter(root=tmp_path, codex_command="codex-test")
    work_unit = WorkUnit(
        id="review",
        role="reviewer",
        goal="Review branch",
        prompt="Find issues",
        expected_output="Findings",
    )

    result = adapter.run_worker(work_unit)

    assert calls["args"][:-1] == [
        "codex-test",
        "exec",
        "-C",
        str(tmp_path),
        "-s",
        "workspace-write",
        "-a",
        "never",
    ]
    assert "Role: reviewer" in calls["args"][-1]
    assert calls["kwargs"]["encoding"] == "utf-8"
    assert result.status == "succeeded"
    assert result.raw_output == "worker output"


def test_codex_cli_adapter_verifies_first_line(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "subprocess.run",
        lambda args, **kwargs: subprocess.CompletedProcess(
            args,
            0,
            stdout="PASSED\nlooks good",
            stderr="",
        ),
    )
    adapter = CodexCliAdapter(root=tmp_path, codex_command="codex-test")
    worker_result = WorkerResult(
        work_unit_id="review",
        status=WorkerStatus.SUCCEEDED,
        summary="summary",
        evidence=["evidence"],
        raw_output="raw",
    )

    result = adapter.verify_worker_result(worker_result)

    assert result.status == "passed"
    assert "looks good" in result.notes


def test_codex_cli_adapter_raises_user_facing_error_on_cli_failure(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(
        "subprocess.run",
        lambda args, **kwargs: subprocess.CompletedProcess(
            args,
            1,
            stdout="",
            stderr="not logged in",
        ),
    )
    adapter = CodexCliAdapter(root=tmp_path, codex_command="codex-test")
    work_unit = WorkUnit(
        id="review",
        role="reviewer",
        goal="Review branch",
        prompt="Find issues",
        expected_output="Findings",
    )

    with pytest.raises(RuntimeError, match="not logged in"):
        adapter.run_worker(work_unit)
