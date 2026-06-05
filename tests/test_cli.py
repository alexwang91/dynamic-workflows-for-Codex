import json

from cdw.cli import build_parser, main


def test_build_parser_has_core_commands():
    parser = build_parser()

    subcommands = parser._subparsers._group_actions[0].choices

    assert {"plan", "review", "debug"}.issubset(subcommands)


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


def test_live_adapter_dependency_error_is_user_facing(tmp_path, capsys):
    exit_code = main(
        ["plan", "Review branch", "--root", str(tmp_path), "--adapter", "live"]
    )

    captured = capsys.readouterr()

    assert exit_code == 1
    assert "openai-agents" in captured.err


def test_plan_can_save_workflow_spec(tmp_path):
    spec_path = tmp_path / "review.workflow.json"

    exit_code = main(["plan", "Review branch", "--save-spec", str(spec_path)])

    assert exit_code == 0
    assert spec_path.exists()


def test_run_executes_workflow_spec(tmp_path, capsys):
    spec_path = tmp_path / "review.workflow.json"
    main(["plan", "Review branch", "--save-spec", str(spec_path)])

    exit_code = main(
        ["run", str(spec_path), "--root", str(tmp_path), "--adapter", "fake"]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out.strip().splitlines()[-1].startswith("run ")


def test_resume_command_continues_existing_run(tmp_path, capsys):
    main(["review", "Review branch", "--root", str(tmp_path), "--adapter", "fake"])
    run_id = capsys.readouterr().out.strip().split()[-1]

    exit_code = main(
        ["resume", run_id, "--root", str(tmp_path), "--adapter", "fake"]
    )

    assert exit_code == 0
    assert f"run {run_id}" in capsys.readouterr().out


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
