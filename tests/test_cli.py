import builtins
import json
import subprocess

import pytest

from cdw.cli import build_parser, main
from cdw.schemas import (
    VerificationResult,
    VerificationStatus,
    WorkerResult,
    WorkerStatus,
    WorkflowPlan,
    WorkflowProcedure,
    WorkflowSpecBundle,
    WorkflowStage,
    WorkUnit,
)
from cdw.workflow_spec import save_workflow_spec_bundle


def test_build_parser_has_core_commands():
    parser = build_parser()

    subcommands = parser._subparsers._group_actions[0].choices

    assert {"plan", "review", "debug", "bootstrap", "doctor"}.issubset(subcommands)


def test_approval_flag_is_resume_only():
    parser = build_parser()

    args = parser.parse_args(["resume", "abc123", "--approve-human-gates"])

    assert args.approve_human_gates is True
    with pytest.raises(SystemExit):
        parser.parse_args(["run", "workflow.json", "--approve-human-gates"])


def test_plan_command_persists_state(tmp_path, capsys):
    exit_code = main(
        ["plan", "Review branch", "--root", str(tmp_path), "--adapter", "fake"]
    )

    captured = capsys.readouterr()
    state_path = (
        tmp_path
        / ".cdw"
        / "runs"
        / captured.out.strip().split()[-1]
        / "state.json"
    )

    assert exit_code == 0
    assert state_path.exists()
    data = json.loads(state_path.read_text(encoding="utf-8"))
    assert data["plan"]["command"] == "plan"


def test_live_adapter_dependency_error_is_user_facing(tmp_path, capsys, monkeypatch):
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "agents":
            raise ImportError("missing agents")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    exit_code = main(
        ["plan", "Review branch", "--root", str(tmp_path), "--adapter", "live"]
    )

    captured = capsys.readouterr()

    assert exit_code == 1
    assert "openai-agents" in captured.err


def test_codex_cli_adapter_runs_without_openai_agents(
    tmp_path,
    capsys,
    monkeypatch,
):
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "agents":
            raise ImportError("agents should not be imported")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    monkeypatch.setattr(
        "subprocess.run",
        lambda args, **kwargs: subprocess.CompletedProcess(
            args,
            0,
            stdout="PASSED\ncodex cli output",
            stderr="",
        ),
    )

    exit_code = main(
        [
            "plan",
            "Review branch",
            "--root",
            str(tmp_path),
            "--adapter",
            "codex-cli",
            "--codex-command",
            "codex-test",
        ]
    )

    assert exit_code == 0
    assert capsys.readouterr().out.startswith("run ")


def test_plan_can_save_workflow_spec(tmp_path):
    spec_path = tmp_path / "review.workflow.json"

    exit_code = main(["plan", "Review branch", "--save-spec", str(spec_path)])

    assert exit_code == 0
    assert spec_path.exists()


def test_plan_can_save_fake_dynamic_workflow_spec(tmp_path):
    spec_path = tmp_path / "dynamic.workflow.json"

    exit_code = main(
        [
            "plan",
            "Review auth migration",
            "--planner",
            "fake",
            "--save-spec",
            str(spec_path),
        ]
    )

    data = json.loads(spec_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert len(data["plan"]["work_units"]) >= 2
    assert len(data["procedure"]["stages"]) >= 2


def test_fake_dynamic_planner_does_not_require_codex_command(
    tmp_path,
    monkeypatch,
):
    spec_path = tmp_path / "dynamic.workflow.json"
    monkeypatch.setattr(
        "cdw.cli.resolve_codex_command",
        lambda explicit=None: (_ for _ in ()).throw(AssertionError("should not resolve")),
    )

    exit_code = main(
        [
            "plan",
            "Review auth migration",
            "--planner",
            "fake",
            "--save-spec",
            str(spec_path),
        ]
    )

    assert exit_code == 0
    assert spec_path.exists()


def test_dynamic_planner_failure_is_user_facing(
    tmp_path,
    capsys,
    monkeypatch,
):
    spec_path = tmp_path / "dynamic.workflow.json"
    monkeypatch.setattr(
        "cdw.cli.build_dynamic_workflow_spec",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            RuntimeError("dynamic planner returned invalid JSON")
        ),
    )

    exit_code = main(
        [
            "plan",
            "Review auth migration",
            "--planner",
            "fake",
            "--save-spec",
            str(spec_path),
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 1
    assert "dynamic planner returned invalid JSON" in captured.err
    assert not spec_path.exists()


def test_dynamic_planner_requires_save_spec(capsys):
    exit_code = main(["plan", "Review branch", "--planner", "fake"])

    captured = capsys.readouterr()

    assert exit_code == 1
    assert "--planner requires --save-spec" in captured.err


def test_run_executes_workflow_spec(tmp_path, capsys):
    spec_path = tmp_path / "review.workflow.json"
    main(["plan", "Review branch", "--save-spec", str(spec_path)])

    exit_code = main(
        ["run", str(spec_path), "--root", str(tmp_path), "--adapter", "fake"]
    )

    captured = capsys.readouterr()
    run_id = captured.out.strip().splitlines()[-1].split()[-1]
    state_path = tmp_path / ".cdw" / "runs" / run_id / "state.json"
    data = json.loads(state_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert captured.out.strip().splitlines()[-1].startswith("run ")
    assert data["procedure"]["stages"][0]["id"] == "workflow-planner"


def test_cli_returns_failure_when_workflow_is_incomplete(tmp_path, capsys, monkeypatch):
    class FailingVerifierAdapter:
        def run_worker(self, work_unit):
            return WorkerResult(
                work_unit_id=work_unit.id,
                status=WorkerStatus.SUCCEEDED,
                summary="worker output",
            )

        def verify_worker_result(self, result):
            return VerificationResult(
                work_unit_id=result.work_unit_id,
                status=VerificationStatus.FAILED,
                notes="not good enough",
            )

    monkeypatch.setattr(
        "cdw.cli._build_adapter",
        lambda config, codex_command=None: FailingVerifierAdapter(),
    )

    exit_code = main(["plan", "Review branch", "--root", str(tmp_path)])

    captured = capsys.readouterr()

    assert exit_code == 1
    assert captured.out.startswith("run ")
    assert "workflow incomplete" in captured.err
    assert "planner" in captured.err


def test_resume_command_continues_existing_run(tmp_path, capsys):
    main(["review", "Review branch", "--root", str(tmp_path), "--adapter", "fake"])
    run_id = capsys.readouterr().out.strip().split()[-1]

    exit_code = main(
        ["resume", run_id, "--root", str(tmp_path), "--adapter", "fake"]
    )

    assert exit_code == 0
    assert f"run {run_id}" in capsys.readouterr().out


def test_run_reports_waiting_for_human_approval(tmp_path, capsys):
    spec_path = tmp_path / "manual.workflow.json"
    save_workflow_spec_bundle(spec_path, _manual_gate_bundle())

    exit_code = main(["run", str(spec_path), "--root", str(tmp_path)])

    captured = capsys.readouterr()

    assert exit_code == 1
    assert "run " in captured.out
    assert "waiting for human approval" in captured.err
    assert "manual-review" in captured.err


def test_resume_can_approve_human_gates(tmp_path, capsys):
    spec_path = tmp_path / "manual.workflow.json"
    save_workflow_spec_bundle(spec_path, _manual_gate_bundle())
    main(["run", str(spec_path), "--root", str(tmp_path)])
    run_id = capsys.readouterr().out.strip().split()[-1]

    exit_code = main(
        [
            "resume",
            run_id,
            "--root",
            str(tmp_path),
            "--approve-human-gates",
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert f"run {run_id}" in captured.out


def test_migrate_waits_for_human_approval_before_guarded_stage(tmp_path, capsys):
    exit_code = main(
        [
            "migrate",
            "Rename User model to Account",
            "--root",
            str(tmp_path),
            "--adapter",
            "fake",
        ]
    )

    captured = capsys.readouterr()
    run_id = captured.out.strip().split()[-1]
    state_path = tmp_path / ".cdw" / "runs" / run_id / "state.json"
    data = json.loads(state_path.read_text(encoding="utf-8"))

    assert exit_code == 1
    assert "waiting for human approval" in captured.err
    assert data["pending_human_approval"] == "migration-plan-review"
    assert [result["work_unit_id"] for result in data["worker_results"]] == [
        "inventory"
    ]


def test_install_skill_command_writes_repo_skill(tmp_path, capsys):
    exit_code = main(["install-skill", "--root", str(tmp_path)])

    captured = capsys.readouterr()
    skill_path = (
        tmp_path
        / ".agents"
        / "skills"
        / "dynamic-workflows-for-Codex"
        / "SKILL.md"
    )
    assert exit_code == 0
    assert captured.out.strip() == f"skill {skill_path}"
    assert skill_path.exists()


def _manual_gate_bundle() -> WorkflowSpecBundle:
    plan = WorkflowPlan(
        command="review",
        request="Manual review workflow",
        pattern="manual-gated",
        work_units=[
            WorkUnit(
                id="first",
                role="first worker",
                goal="Run first stage",
                prompt="Run first stage",
                expected_output="First result",
            ),
            WorkUnit(
                id="second",
                role="second worker",
                goal="Run second stage",
                prompt="Run second stage",
                expected_output="Second result",
            ),
        ],
        verification_strategy="manual-gated",
        stop_condition="procedure_complete",
    )
    return WorkflowSpecBundle(
        procedure=WorkflowProcedure(
            mode="sequence",
            triggers=["manual"],
            stages=[
                WorkflowStage(
                    id="stage-one",
                    purpose="Run first stage",
                    work_unit_ids=["first"],
                    gate="all_required_verified",
                    on_failure="stop",
                ),
                WorkflowStage(
                    id="manual-review",
                    purpose="Require human approval before second stage",
                    work_unit_ids=["second"],
                    gate="manual_review",
                    on_failure="require_human",
                ),
            ],
            final_artifacts=["synthesis report"],
        ),
        plan=plan,
    )


def test_bootstrap_command_prepares_repo_plugin(tmp_path, capsys):
    exit_code = main(["bootstrap", "--root", str(tmp_path)])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "marketplace " in captured.out
    assert "plugin " in captured.out
    assert "codex plugin marketplace add .agents/plugins" in captured.out
    assert "python -m cdw doctor" in captured.out
    assert (tmp_path / ".agents" / "plugins" / "marketplace.json").exists()


def test_live_smoke_command_reports_failure(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr("shutil.which", lambda command: None)

    exit_code = main(["live-smoke", "--root", str(tmp_path)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "codex-command" in captured.out


def test_doctor_command_reports_status(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(
        "subprocess.run",
        lambda args, **kwargs: subprocess.CompletedProcess(
            args,
            0,
            stdout="ok",
            stderr="",
        ),
    )

    exit_code = main(
        [
            "doctor",
            "--root",
            str(tmp_path),
            "--codex-command",
            "codex-test",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "codex-command" in captured.out
    assert "plugin-package" in captured.out


def test_live_smoke_command_accepts_codex_command(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr("importlib.util.find_spec", lambda name: object())
    monkeypatch.setattr(
        "subprocess.run",
        lambda args, **kwargs: subprocess.CompletedProcess(
            args,
            0,
            stdout="ok",
            stderr="",
        ),
    )

    exit_code = main(
        [
            "live-smoke",
            "--root",
            str(tmp_path),
            "--codex-command",
            "codex-test",
        ]
    )

    assert exit_code == 0
    assert "codex-test" in capsys.readouterr().out


def test_live_smoke_dry_contract_prints_json_without_preflight(
    tmp_path,
    capsys,
    monkeypatch,
):
    def fail_find_spec(name):
        raise AssertionError("dry contract must not check imports")

    def fail_run(args, **kwargs):
        raise AssertionError("dry contract must not execute subprocesses")

    monkeypatch.setattr("importlib.util.find_spec", fail_find_spec)
    monkeypatch.setattr("subprocess.run", fail_run)

    exit_code = main(["live-smoke", "--root", str(tmp_path), "--dry-contract"])

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert exit_code == 0
    assert data["tool"] == "codex"
    assert data["arguments"]["cwd"] == str(tmp_path)


def test_package_plugin_command_writes_package(tmp_path, capsys):
    exit_code = main(["package-plugin", "--output", str(tmp_path)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out.strip().startswith("plugin ")
    assert (
        tmp_path
        / "dynamic-workflows-for-codex"
        / ".codex-plugin"
        / "plugin.json"
    ).exists()


def test_package_plugin_command_can_write_repo_marketplace(tmp_path, capsys):
    exit_code = main(["package-plugin", "--repo-marketplace", "--root", str(tmp_path)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out.strip() == (
        f"marketplace {tmp_path / '.agents' / 'plugins' / 'marketplace.json'}"
    )
    assert (
        tmp_path
        / ".agents"
        / "plugins"
        / "plugins"
        / "dynamic-workflows-for-codex"
        / ".codex-plugin"
        / "plugin.json"
    ).exists()
