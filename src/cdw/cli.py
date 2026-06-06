from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from cdw.codex_mcp import FakeCodexAdapter
from cdw.codex_command import resolve_codex_command
from cdw.config import RuntimeConfig
from cdw.live_smoke import build_live_smoke_contract, run_live_smoke
from cdw.planner import build_plan
from cdw.plugin_package import package_plugin
from cdw.plugin_package import package_repo_marketplace
from cdw.resume import resume_run
from cdw.runtime import execute_plan, execute_workflow_bundle
from cdw.skill import install_skill
from cdw.workflow_spec import load_workflow_spec_bundle, save_workflow_spec

ADAPTER_CHOICES = ("fake", "live", "codex-cli")


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
        command.add_argument("--adapter", choices=ADAPTER_CHOICES, default="fake")
        command.add_argument("--codex-command")
        if name == "plan":
            command.add_argument("--save-spec")
    run_command = subparsers.add_parser("run")
    run_command.add_argument("workflow_spec")
    run_command.add_argument("--root", default=".")
    run_command.add_argument("--adapter", choices=ADAPTER_CHOICES, default="fake")
    run_command.add_argument("--codex-command")
    resume_command = subparsers.add_parser("resume")
    resume_command.add_argument("run_id")
    resume_command.add_argument("--root", default=".")
    resume_command.add_argument("--adapter", choices=ADAPTER_CHOICES, default="fake")
    resume_command.add_argument("--codex-command")
    install_skill_command = subparsers.add_parser("install-skill")
    install_skill_command.add_argument("--root", default=".")
    bootstrap_command = subparsers.add_parser("bootstrap")
    bootstrap_command.add_argument("--root", default=".")
    doctor_command = subparsers.add_parser("doctor")
    doctor_command.add_argument("--root", default=".")
    doctor_command.add_argument("--codex-command")
    live_smoke_command = subparsers.add_parser("live-smoke")
    live_smoke_command.add_argument("--root", default=".")
    live_smoke_command.add_argument("--execute", action="store_true")
    live_smoke_command.add_argument("--dry-contract", action="store_true")
    live_smoke_command.add_argument("--codex-command")
    package_plugin_command = subparsers.add_parser("package-plugin")
    package_plugin_command.add_argument("--output", default="plugins")
    package_plugin_command.add_argument("--root", default=".")
    package_plugin_command.add_argument("--repo-marketplace", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "install-skill":
        path = install_skill(Path(args.root))
        print(f"skill {path}")
        return 0
    if args.command == "bootstrap":
        from cdw.bootstrap import run_bootstrap

        report = run_bootstrap(Path(args.root))
        print(report.to_text())
        return 0
    if args.command == "doctor":
        from cdw.doctor import run_doctor

        report = run_doctor(Path(args.root), codex_command=args.codex_command)
        print(report.to_text())
        return 0 if report.ok else 1
    if args.command == "live-smoke":
        if args.dry_contract:
            print(json.dumps(build_live_smoke_contract(Path(args.root)), indent=2))
            return 0
        report = run_live_smoke(
            Path(args.root),
            execute=args.execute,
            codex_command=args.codex_command,
        )
        print(report.to_text())
        return 0 if report.ok else 1
    if args.command == "package-plugin":
        if args.repo_marketplace:
            path = package_repo_marketplace(Path(args.root))
            print(f"marketplace {path}")
            return 0
        path = package_plugin(Path(args.output))
        print(f"plugin {path}")
        return 0
    config = RuntimeConfig(root=Path(args.root), adapter=args.adapter)
    if args.command == "resume":
        adapter = _build_adapter(config, codex_command=args.codex_command)
        try:
            state = resume_run(config.root, args.run_id, adapter)
        except RuntimeError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print(f"run {state.run_id}")
        return 0
    if args.command == "run":
        bundle = load_workflow_spec_bundle(Path(args.workflow_spec))
        adapter = _build_adapter(config, codex_command=args.codex_command)
        try:
            state = execute_workflow_bundle(bundle, config.root, adapter)
        except RuntimeError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print(f"run {state.run_id}")
        return 0
    plan = build_plan(args.command, args.request)
    if args.command == "plan" and args.save_spec:
        path = save_workflow_spec(Path(args.save_spec), plan)
        print(f"spec {path}")
        return 0
    adapter = _build_adapter(config, codex_command=args.codex_command)
    try:
        state = execute_plan(plan, config.root, adapter)
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"run {state.run_id}")
    return 0


def _build_adapter(config: RuntimeConfig, codex_command: str | None = None):
    if config.adapter == "fake":
        return FakeCodexAdapter()
    if config.adapter == "codex-cli":
        from cdw.codex_cli import CodexCliAdapter

        resolution = resolve_codex_command(explicit=codex_command)
        return CodexCliAdapter(
            root=config.root,
            codex_command=resolution.command or "codex",
        )
    from cdw.codex_mcp import LiveCodexAdapter

    resolution = resolve_codex_command(explicit=codex_command)
    return LiveCodexAdapter(root=config.root, codex_command=resolution.command or "codex")
