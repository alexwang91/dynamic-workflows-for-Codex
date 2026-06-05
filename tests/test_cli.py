import builtins
import json
import subprocess

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


def test_live_smoke_command_reports_failure(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr("shutil.which", lambda command: None)

    exit_code = main(["live-smoke", "--root", str(tmp_path)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "codex-command" in captured.out


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
