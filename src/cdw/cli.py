from __future__ import annotations

import argparse
from pathlib import Path

from cdw.codex_mcp import FakeCodexAdapter
from cdw.config import RuntimeConfig
from cdw.planner import build_plan
from cdw.runtime import execute_plan


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cdw",
        description="Codex Dynamic Workflows external runtime.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("plan", "review", "debug"):
        command = subparsers.add_parser(name)
        command.add_argument("request")
        command.add_argument("--root", default=".")
        command.add_argument("--adapter", choices=("fake", "live"), default="fake")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    config = RuntimeConfig(root=Path(args.root), adapter=args.adapter)
    plan = build_plan(args.command, args.request)
    adapter = _build_adapter(config)
    state = execute_plan(plan, config.root, adapter)
    print(f"run {state.run_id}")
    return 0


def _build_adapter(config: RuntimeConfig):
    if config.adapter == "fake":
        return FakeCodexAdapter()
    raise RuntimeError("Live adapter is not implemented in this task.")
