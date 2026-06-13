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

    assert {
        "plan",
        "review",
        "debug",
        "bootstrap",
        "doctor",
        "artifacts",
        "artifact",
    }.issubset(subcommands)


def test_approval_flag_is_resume_only():
    parser = build_parser()

    args = parser.parse_args(["resume", "abc123", "--approve-human-gates"])

    assert args.approve_human_gates is True
    with pytest.raises(SystemExit):
        parser.parse_args(["run", "workflow.json", "--approve-human-gates"])


def test_path_boundary_flags_parse_for_plan_migrate_and_run():
    parser = build_parser()

    plan_args = parser.parse_args(
        [
            "plan",
            "Review branch",
            "--allow-path",
            "src/**",
            "--forbid-path",
            ".env*",
        ]
    )
    migrate_args = parser.parse_args(
        [
            "migrate",
            "Rename model",
            "--allow-path",
            "app/**",
            "--allow-path",
            "tests/**",
        ]
    )
    run_args = parser.parse_args(
        [
            "run",
            "workflow.json",
            "--allow-path",
            "src/**",
            "--forbid-path",
            "secrets/**",
        ]
    )
    resume_args = parser.parse_args(
        [
            "resume",
            "abc123",
            "--allow-path",
            "src/**",
            "--forbid-path",
            "secrets/**",
        ]
    )

    assert plan_args.allow_path == ["src/**"]
    assert plan_args.forbid_path == [".env*"]
    assert migrate_args.allow_path == ["app/**", "tests/**"]
    assert run_args.forbid_path == ["secrets/**"]
    assert resume_args.allow_path == ["src/**"]
    assert resume_args.forbid_path == ["secrets/**"]


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


def test_plan_save_spec_applies_path_boundary_overrides(tmp_path):
    spec_path = tmp_path / "review.workflow.json"

    exit_code = main(
        [
            "plan",
            "Review branch",
            "--save-spec",
            str(spec_path),
            "--allow-path",
            "src/**",
            "--forbid-path",
            ".env*",
        ]
    )

    data = json.loads(spec_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert data["constraints"]["allowed_paths"] == ["src/**"]
    assert data["constraints"]["forbidden_paths"] == [".env*"]


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


def test_status_reports_waiting_human_run(tmp_path, capsys):
    spec_path = tmp_path / "manual.workflow.json"
    save_workflow_spec_bundle(spec_path, _manual_gate_bundle())
    main(["run", str(spec_path), "--root", str(tmp_path)])
    run_id = capsys.readouterr().out.strip().split()[-1]

    exit_code = main(["status", run_id, "--root", str(tmp_path)])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert f"run {run_id}" in captured.out
    assert "status waiting_for_human" in captured.out
    assert "adapter fake" in captured.out
    assert "pending manual-review" in captured.out
    assert (
        f"resume python -m cdw resume {run_id} --adapter fake --approve-human-gates"
        in captured.out
    )
    assert "state " in captured.out


def test_status_reports_artifacts_for_completed_run(tmp_path, capsys):
    spec_path = tmp_path / "artifact.workflow.json"
    save_workflow_spec_bundle(spec_path, _artifact_bundle())
    main(["run", str(spec_path), "--root", str(tmp_path)])
    run_id = capsys.readouterr().out.strip().split()[-1]

    exit_code = main(["status", run_id, "--root", str(tmp_path)])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "artifacts 1" in captured.out
    assert "artifact first artifact stage stage-one" in captured.out


def test_status_json_reports_waiting_human_run(tmp_path, capsys):
    spec_path = tmp_path / "manual.workflow.json"
    save_workflow_spec_bundle(spec_path, _manual_gate_bundle())
    main(["run", str(spec_path), "--root", str(tmp_path)])
    run_id = capsys.readouterr().out.strip().split()[-1]

    exit_code = main(["status", run_id, "--root", str(tmp_path), "--json"])

    captured = capsys.readouterr()
    data = json.loads(captured.out)

    assert exit_code == 0
    assert data["run_id"] == run_id
    assert data["status"] == "waiting_for_human"
    assert data["adapter"] == "fake"
    assert data["pending_human_approval"] == "manual-review"
    assert data["worker_count"] == 1
    assert data["verification_count"] == 1
    assert data["resume_command"] == (
        f"python -m cdw resume {run_id} --adapter fake --approve-human-gates"
    )


def test_status_json_reports_artifacts_for_completed_run(tmp_path, capsys):
    spec_path = tmp_path / "artifact.workflow.json"
    save_workflow_spec_bundle(spec_path, _artifact_bundle())
    main(["run", str(spec_path), "--root", str(tmp_path)])
    run_id = capsys.readouterr().out.strip().split()[-1]

    exit_code = main(["status", run_id, "--root", str(tmp_path), "--json"])

    captured = capsys.readouterr()
    data = json.loads(captured.out)

    assert exit_code == 0
    assert data["artifact_count"] == 1
    assert data["artifacts"][0]["name"] == "first artifact"
    assert data["artifacts"][0]["stage_id"] == "stage-one"


def test_status_json_reports_boundary_failures(tmp_path, capsys, monkeypatch):
    spec_path = tmp_path / "boundary.workflow.json"
    save_workflow_spec_bundle(spec_path, _boundary_bundle())
    monkeypatch.setattr(
        "cdw.cli._build_adapter",
        lambda config, codex_command=None: BoundaryCliAdapter(),
    )
    main(
        [
            "run",
            str(spec_path),
            "--root",
            str(tmp_path),
        ]
    )
    run_id = capsys.readouterr().out.strip().split()[-1]

    main(
        [
            "resume",
            run_id,
            "--root",
            str(tmp_path),
            "--approve-human-gates",
            "--allow-path",
            "src/**",
            "--forbid-path",
            "secrets/**",
        ]
    )
    capsys.readouterr()

    exit_code = main(["status", run_id, "--root", str(tmp_path), "--json"])

    captured = capsys.readouterr()
    data = json.loads(captured.out)

    assert exit_code == 0
    assert data["boundary_failure_count"] == 1
    assert data["boundary_failures"][0]["stage_id"] == "migration-plan-review"
    assert data["boundary_failures"][0]["violations"][0]["path"] == "secrets/key.py"


def test_artifacts_command_lists_run_artifacts(tmp_path, capsys):
    spec_path = tmp_path / "artifact.workflow.json"
    save_workflow_spec_bundle(spec_path, _artifact_bundle())
    main(["run", str(spec_path), "--root", str(tmp_path)])
    run_id = capsys.readouterr().out.strip().split()[-1]

    exit_code = main(["artifacts", run_id, "--root", str(tmp_path)])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "artifact first artifact stage stage-one" in captured.out


def test_artifact_command_prints_artifact_content(tmp_path, capsys):
    spec_path = tmp_path / "artifact.workflow.json"
    save_workflow_spec_bundle(spec_path, _artifact_bundle())
    main(["run", str(spec_path), "--root", str(tmp_path)])
    run_id = capsys.readouterr().out.strip().split()[-1]

    exit_code = main(
        ["artifact", run_id, "first artifact", "--root", str(tmp_path)]
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "# first artifact" in captured.out
    assert "first worker completed Run first stage" in captured.out


def test_artifact_command_reports_missing_artifact_without_traceback(tmp_path, capsys):
    spec_path = tmp_path / "artifact.workflow.json"
    save_workflow_spec_bundle(spec_path, _artifact_bundle())
    main(["run", str(spec_path), "--root", str(tmp_path)])
    run_id = capsys.readouterr().out.strip().split()[-1]

    exit_code = main(["artifact", run_id, "missing", "--root", str(tmp_path)])

    captured = capsys.readouterr()

    assert exit_code == 1
    assert "error: artifact not found: missing" in captured.err
    assert "Traceback" not in captured.err


def test_status_reports_missing_run_without_traceback(tmp_path, capsys):
    exit_code = main(["status", "missing", "--root", str(tmp_path)])

    captured = capsys.readouterr()

    assert exit_code == 1
    assert "error: run not found: missing" in captured.err


def test_status_reports_corrupt_run_without_traceback(tmp_path, capsys):
    state_dir = tmp_path / ".cdw" / "runs" / "corrupt"
    state_dir.mkdir(parents=True)
    (state_dir / "state.json").write_text("{bad json", encoding="utf-8")

    exit_code = main(["status", "corrupt", "--root", str(tmp_path)])

    captured = capsys.readouterr()

    assert exit_code == 1
    assert "error:" in captured.err
    assert "Traceback" not in captured.err


def test_runs_lists_existing_runs(tmp_path, capsys):
    main(["review", "Review branch", "--root", str(tmp_path), "--adapter", "fake"])
    first_run_id = capsys.readouterr().out.strip().split()[-1]
    main(["debug", "Debug branch", "--root", str(tmp_path), "--adapter", "fake"])
    second_run_id = capsys.readouterr().out.strip().split()[-1]

    exit_code = main(["runs", "--root", str(tmp_path)])

    captured = capsys.readouterr()
    lines = captured.out.strip().splitlines()

    assert exit_code == 0
    assert lines[0].startswith(f"run {second_run_id} status complete command debug")
    assert lines[1].startswith(f"run {first_run_id} status complete command review")


def test_runs_json_lists_existing_runs(tmp_path, capsys):
    main(["review", "Review branch", "--root", str(tmp_path), "--adapter", "fake"])
    run_id = capsys.readouterr().out.strip().split()[-1]

    exit_code = main(["runs", "--root", str(tmp_path), "--json"])

    captured = capsys.readouterr()
    data = json.loads(captured.out)

    assert exit_code == 0
    assert data[0]["run_id"] == run_id
    assert data[0]["status"] == "complete"


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
    assert data["artifacts"][0]["name"] == "migration inventory"
    artifact_path = (
        tmp_path
        / ".cdw"
        / "runs"
        / run_id
        / data["artifacts"][0]["path"]
    )
    assert artifact_path.exists()


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


def _artifact_bundle() -> WorkflowSpecBundle:
    plan = WorkflowPlan(
        command="review",
        request="Artifact workflow",
        pattern="artifact-flow",
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
        verification_strategy="artifact-flow",
        stop_condition="procedure_complete",
    )
    return WorkflowSpecBundle(
        procedure=WorkflowProcedure(
            mode="sequence",
            triggers=["artifact"],
            stages=[
                WorkflowStage(
                    id="stage-one",
                    purpose="Run first stage",
                    work_unit_ids=["first"],
                    produces=["first artifact"],
                ),
                WorkflowStage(
                    id="stage-two",
                    purpose="Run second stage",
                    work_unit_ids=["second"],
                    depends_on=["stage-one"],
                    consumes=["first artifact"],
                ),
            ],
            final_artifacts=["synthesis report"],
        ),
        plan=plan,
    )


class BoundaryCliAdapter:
    def run_worker(self, work_unit):
        output = {
            "inventory": "Inventory complete",
            "patch-plan": "WRITE_PATHS:\n- secrets/key.py",
        }.get(work_unit.id, f"{work_unit.id} complete")
        return WorkerResult(
            work_unit_id=work_unit.id,
            status=WorkerStatus.SUCCEEDED,
            summary=output,
            evidence=[output],
            raw_output=output,
        )

    def verify_worker_result(self, result):
        return VerificationResult(
            work_unit_id=result.work_unit_id,
            status=VerificationStatus.PASSED,
            notes="ok",
        )


def _boundary_bundle() -> WorkflowSpecBundle:
    plan = WorkflowPlan(
        command="migrate",
        request="Boundary workflow",
        pattern="artifact-flow",
        work_units=[
            WorkUnit(
                id="inventory",
                role="inventory worker",
                goal="Run inventory",
                prompt="Run inventory",
                expected_output="Inventory",
            ),
            WorkUnit(
                id="patch-plan",
                role="patch planner",
                goal="Plan patch",
                prompt="Plan patch",
                expected_output="Patch plan",
            ),
        ],
        verification_strategy="artifact-flow",
        stop_condition="procedure_complete",
    )
    return WorkflowSpecBundle(
        procedure=WorkflowProcedure(
            mode="guarded",
            triggers=["migrate"],
            stages=[
                WorkflowStage(
                    id="migration-inventory",
                    purpose="Run inventory",
                    work_unit_ids=["inventory"],
                    produces=["migration inventory"],
                ),
                WorkflowStage(
                    id="migration-plan-review",
                    purpose="Review patch plan",
                    work_unit_ids=["patch-plan"],
                    depends_on=["migration-inventory"],
                    consumes=["migration inventory"],
                    produces=["guarded patch plan"],
                    gate="manual_review",
                    on_failure="require_human",
                    write_policy="guarded",
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
