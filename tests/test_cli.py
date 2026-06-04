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
