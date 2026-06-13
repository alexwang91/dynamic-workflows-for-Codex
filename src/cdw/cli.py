from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pydantic import ValidationError

from cdw.artifacts import read_artifact
from cdw.codex_mcp import FakeCodexAdapter
from cdw.codex_command import resolve_codex_command
from cdw.config import RuntimeConfig
from cdw.dynamic_planner import PLANNER_CHOICES, build_dynamic_workflow_spec
from cdw.live_smoke import build_live_smoke_contract, run_live_smoke
from cdw.planner import build_plan
from cdw.plugin_package import package_plugin
from cdw.plugin_package import package_repo_marketplace
from cdw.run_status import list_run_summaries, summarize_run
from cdw.runtime import execute_existing_state, execute_workflow_bundle
from cdw.skill import install_skill
from cdw.state import load_run_state, save_run_state
from cdw.workflow_spec import (
    build_workflow_spec_bundle,
    load_workflow_spec_bundle,
    save_workflow_spec_bundle,
)

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
        command.add_argument("--allow-path", action="append", default=[])
        command.add_argument("--forbid-path", action="append", default=[])
        if name == "plan":
            command.add_argument("--save-spec")
            command.add_argument("--planner", choices=PLANNER_CHOICES, default="static")
    run_command = subparsers.add_parser("run")
    run_command.add_argument("workflow_spec")
    run_command.add_argument("--root", default=".")
    run_command.add_argument("--adapter", choices=ADAPTER_CHOICES, default="fake")
    run_command.add_argument("--codex-command")
    run_command.add_argument("--allow-path", action="append", default=[])
    run_command.add_argument("--forbid-path", action="append", default=[])
    status_command = subparsers.add_parser("status")
    status_command.add_argument("run_id")
    status_command.add_argument("--root", default=".")
    status_command.add_argument("--json", action="store_true", dest="json_output")
    runs_command = subparsers.add_parser("runs")
    runs_command.add_argument("--root", default=".")
    runs_command.add_argument("--json", action="store_true", dest="json_output")
    artifacts_command = subparsers.add_parser("artifacts")
    artifacts_command.add_argument("run_id")
    artifacts_command.add_argument("--root", default=".")
    artifacts_command.add_argument("--json", action="store_true", dest="json_output")
    artifact_command = subparsers.add_parser("artifact")
    artifact_command.add_argument("run_id")
    artifact_command.add_argument("artifact_name")
    artifact_command.add_argument("--root", default=".")
    artifact_command.add_argument("--stage-id")
    resume_command = subparsers.add_parser("resume")
    resume_command.add_argument("run_id")
    resume_command.add_argument("--root", default=".")
    resume_command.add_argument("--adapter", choices=ADAPTER_CHOICES, default="fake")
    resume_command.add_argument("--codex-command")
    resume_command.add_argument("--allow-path", action="append", default=[])
    resume_command.add_argument("--forbid-path", action="append", default=[])
    resume_command.add_argument("--approve-human-gates", action="store_true")
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
    if args.command == "status":
        try:
            summary = summarize_run(Path(args.root), args.run_id)
        except (RuntimeError, OSError, ValueError, ValidationError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        if args.json_output:
            print(json.dumps(summary.to_dict(), indent=2))
        else:
            print(_format_status(summary))
        return 0
    if args.command == "runs":
        summaries = list_run_summaries(Path(args.root))
        if args.json_output:
            print(json.dumps([summary.to_dict() for summary in summaries], indent=2))
        else:
            for summary in summaries:
                print(_format_run_line(summary))
        return 0
    if args.command == "artifacts":
        try:
            summary = summarize_run(Path(args.root), args.run_id)
        except (RuntimeError, OSError, ValueError, ValidationError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        if args.json_output:
            print(json.dumps(summary.artifacts, indent=2))
        else:
            for artifact in summary.artifacts:
                print(_format_artifact_line(artifact))
        return 0
    if args.command == "artifact":
        try:
            state = load_run_state(Path(args.root), args.run_id)
            print(
                read_artifact(
                    Path(args.root),
                    state,
                    args.artifact_name,
                    stage_id=args.stage_id,
                )
            )
        except (RuntimeError, OSError, ValueError, ValidationError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        return 0
    config = RuntimeConfig(root=Path(args.root), adapter=args.adapter)
    if args.command == "resume":
        adapter = _build_adapter(config, codex_command=args.codex_command)
        try:
            state = load_run_state(config.root, args.run_id)
            if _has_constraint_overrides(args):
                state.constraints = _constraints_with_overrides(
                    state.constraints,
                    args,
                )
                save_run_state(config.root, state)
            state = execute_existing_state(
                config.root,
                state,
                adapter,
                approve_human_gates=args.approve_human_gates,
            )
        except RuntimeError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        return _finish_run(state)
    if args.command == "run":
        bundle = _with_constraint_overrides(
            load_workflow_spec_bundle(Path(args.workflow_spec)),
            args,
        )
        adapter = _build_adapter(config, codex_command=args.codex_command)
        try:
            state = execute_workflow_bundle(
                bundle,
                config.root,
                adapter,
                adapter_name=args.adapter,
            )
        except RuntimeError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        return _finish_run(state)
    plan = build_plan(args.command, args.request)
    if args.command == "plan" and args.save_spec:
        if args.planner == "static":
            bundle = _with_constraint_overrides(build_workflow_spec_bundle(plan), args)
            path = save_workflow_spec_bundle(Path(args.save_spec), bundle)
        else:
            codex_command = "codex"
            if args.planner == "codex-cli":
                resolution = resolve_codex_command(explicit=args.codex_command)
                codex_command = resolution.command or "codex"
            try:
                bundle = build_dynamic_workflow_spec(
                    args.request,
                    planner=args.planner,
                    root=Path(args.root),
                    codex_command=codex_command,
                )
            except RuntimeError as exc:
                print(f"error: {exc}", file=sys.stderr)
                return 1
            bundle = _with_constraint_overrides(bundle, args)
            path = save_workflow_spec_bundle(Path(args.save_spec), bundle)
        print(f"spec {path}")
        return 0
    if args.command == "plan" and args.planner != "static":
        print("error: --planner requires --save-spec", file=sys.stderr)
        return 1
    adapter = _build_adapter(config, codex_command=args.codex_command)
    try:
        state = execute_workflow_bundle(
            _with_constraint_overrides(build_workflow_spec_bundle(plan), args),
            config.root,
            adapter,
            adapter_name=args.adapter,
        )
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return _finish_run(state)


def _finish_run(state) -> int:
    print(f"run {state.run_id}")
    if state.synthesis is None or state.synthesis.status == "complete":
        return 0

    if state.synthesis.status == "waiting_for_human":
        pending = state.pending_human_approval or ", ".join(state.synthesis.unresolved)
        print(
            f"error: waiting for human approval before stage: {pending}",
            file=sys.stderr,
        )
        return 1

    unresolved = ", ".join(state.synthesis.unresolved) or "unknown"
    print(f"error: workflow incomplete; unresolved: {unresolved}", file=sys.stderr)
    return 1


def _format_status(summary) -> str:
    lines = [
        f"run {summary.run_id}",
        f"status {summary.status}",
        f"command {summary.command}",
        f"request {summary.request}",
    ]
    if summary.adapter is not None:
        lines.append(f"adapter {summary.adapter}")
    if summary.pending_human_approval is not None:
        lines.append(f"pending {summary.pending_human_approval}")
    if summary.resume_command is not None:
        lines.append(f"resume {summary.resume_command}")
    if summary.artifact_count:
        lines.append(f"artifacts {summary.artifact_count}")
        lines.extend(_format_artifact_line(artifact) for artifact in summary.artifacts)
    if summary.boundary_failure_count:
        lines.append(f"boundary-failures {summary.boundary_failure_count}")
        lines.extend(
            _format_boundary_failure_line(boundary)
            for boundary in summary.boundary_failures
        )
    lines.append(f"state {summary.state_path}")
    return "\n".join(lines)


def _format_run_line(summary) -> str:
    line = f"run {summary.run_id} status {summary.status} command {summary.command}"
    if summary.adapter is not None:
        line += f" adapter {summary.adapter}"
    if summary.pending_human_approval is not None:
        line += f" pending {summary.pending_human_approval}"
    if summary.artifact_count:
        line += f" artifacts {summary.artifact_count}"
    if summary.boundary_failure_count:
        line += f" boundary-failures {summary.boundary_failure_count}"
    return line


def _format_artifact_line(artifact: dict[str, object]) -> str:
    return (
        f"artifact {artifact['name']} stage {artifact['stage_id']} "
        f"path {artifact['path']}"
    )


def _format_boundary_failure_line(boundary: dict[str, object]) -> str:
    violations = boundary.get("violations", [])
    if not violations:
        return f"boundary failed stage {boundary['stage_id']}"
    first_violation = violations[0]
    return (
        f"boundary failed stage {boundary['stage_id']} "
        f"path {first_violation['path']} reason {first_violation['reason']}"
    )


def _with_constraint_overrides(bundle, args):
    if not _has_constraint_overrides(args):
        return bundle
    return bundle.model_copy(
        update={
            "constraints": _constraints_with_overrides(bundle.constraints, args)
        }
    )


def _constraints_with_overrides(constraints, args):
    allow_paths = getattr(args, "allow_path", None) or []
    forbid_paths = getattr(args, "forbid_path", None) or []
    return constraints.model_copy(
        update={
            "allowed_paths": _unique_paths(
                [*constraints.allowed_paths, *allow_paths]
            ),
            "forbidden_paths": _unique_paths(
                [*constraints.forbidden_paths, *forbid_paths]
            ),
        }
    )


def _has_constraint_overrides(args) -> bool:
    return bool(getattr(args, "allow_path", None) or getattr(args, "forbid_path", None))


def _unique_paths(paths: list[str]) -> list[str]:
    seen = set()
    unique = []
    for path in paths:
        if path not in seen:
            seen.add(path)
            unique.append(path)
    return unique


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
