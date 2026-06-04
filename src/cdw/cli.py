from __future__ import annotations

import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cdw",
        description="Codex Dynamic Workflows external runtime.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("plan", "review", "debug"):
        command = subparsers.add_parser(name)
        command.add_argument("request")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    parser.parse_args(argv)
    return 0
