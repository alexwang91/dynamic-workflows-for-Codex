from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cdw.codex_mcp import FakeCodexAdapter
from cdw.config import RuntimeConfig
from cdw.planner import build_plan
from cdw.resume import resume_run
from cdw.runtime import execute_plan
from cdw.workflow_spec import load_workflow_spec, save_workflow_spec


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cdw",
        description="dynamic-workflows-for-Codex external runtime.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("plan", "review", "debug", "migrate"):
        command = subparsers.add_parser(name)
        command.add_argument("request")
        command.add_argument("--root", default=".")
        command.add_argument("--adapter", choices=("fake", "live"), default="fake")
        if name == "plan":
            command.add_argument("--save-spec")
    run_command = subparsers.add_parser("run")
    run_command.add_argument("workflow_spec")
    run_command.add_argument("--root", default=".")
    run_command.add_argument("--adapter", choices=("fake", "live"), default="fake")
    resume_command = subparsers.add_parser("resume")
    resume_command.add_argument("run_id")
    resume_command.add_argument("--root", default=".")
    resume_command.add_argument("--adapter", choices=("fake", "live"), default="fake")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    config = RuntimeConfig(root=Path(args.root), adapter=args.adapter)
    if args.command == "resume":
        adapter = _build_adapter(config)
        try:
            state = resume_run(config.root, args.run_id, adapter)
        except RuntimeError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print(f"run {state.run_id}")
        return 0
    if args.command == "run":
        plan = load_workflow_spec(Path(args.workflow_spec))
    else:
        plan = build_plan(args.command, args.request)
    if args.command == "plan" and args.save_spec:
        path = save_workflow_spec(Path(args.save_spec), plan)
        print(f"spec {path}")
        return 0
    adapter = _build_adapter(config)
    try:
        state = execute_plan(plan, config.root, adapter)
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"run {state.run_id}")
    return 0


def _build_adapter(config: RuntimeConfig):
    if config.adapter == "fake":
        return FakeCodexAdapter()
    from cdw.codex_mcp import LiveCodexAdapter

    return LiveCodexAdapter(root=config.root)
