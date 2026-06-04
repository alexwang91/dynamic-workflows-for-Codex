from cdw.cli import build_parser


def test_build_parser_has_core_commands():
    parser = build_parser()

    subcommands = parser._subparsers._group_actions[0].choices

    assert {"plan", "review", "debug"}.issubset(subcommands)
