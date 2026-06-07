import json
import subprocess

import pytest

from cdw.dynamic_planner import (
    CodexCliDynamicPlanner,
    build_dynamic_workflow_spec,
    parse_dynamic_planner_output,
)


def test_fake_dynamic_planner_builds_multi_stage_spec(tmp_path):
    bundle = build_dynamic_workflow_spec(
        "Review the auth migration before writing code",
        planner="fake",
        root=tmp_path,
    )

    assert bundle.schema_version == "3"
    assert bundle.kind == "codex.dynamic-workflow"
    assert bundle.plan.command == "plan"
    assert len(bundle.plan.work_units) >= 2
    assert bundle.procedure is not None
    assert len(bundle.procedure.stages) >= 2
    assert bundle.procedure.stages[0].work_unit_ids == ["context"]
    assert bundle.constraints.write_policy == "read-only"


def test_parse_dynamic_planner_output_accepts_raw_json(tmp_path):
    bundle = build_dynamic_workflow_spec(
        "Review the auth migration",
        planner="fake",
        root=tmp_path,
    )

    parsed = parse_dynamic_planner_output(bundle.model_dump_json())

    assert parsed == bundle


def test_parse_dynamic_planner_output_accepts_fenced_json(tmp_path):
    bundle = build_dynamic_workflow_spec(
        "Review the auth migration",
        planner="fake",
        root=tmp_path,
    )
    output = "Here is the workflow:\n```json\n" + bundle.model_dump_json() + "\n```"

    parsed = parse_dynamic_planner_output(output)

    assert parsed == bundle


def test_parse_dynamic_planner_output_rejects_invalid_json():
    with pytest.raises(RuntimeError, match="dynamic planner returned invalid JSON"):
        parse_dynamic_planner_output("not json")


def test_parse_dynamic_planner_output_rejects_invalid_workflow_spec():
    with pytest.raises(
        RuntimeError,
        match="dynamic planner returned invalid workflow spec",
    ):
        parse_dynamic_planner_output(json.dumps({"kind": "codex.dynamic-workflow"}))


def test_codex_cli_dynamic_planner_uses_current_codex_exec_args(
    monkeypatch,
    tmp_path,
):
    calls = {}
    bundle = build_dynamic_workflow_spec(
        "Review the auth migration",
        planner="fake",
        root=tmp_path,
    )

    def fake_run(args, **kwargs):
        schema_path = args[args.index("--output-schema") + 1]
        calls["args"] = args
        calls["kwargs"] = kwargs
        with open(schema_path, encoding="utf-8") as handle:
            calls["schema"] = json.load(handle)
        return subprocess.CompletedProcess(
            args,
            0,
            stdout=bundle.model_dump_json(),
            stderr="",
        )

    monkeypatch.setattr("subprocess.run", fake_run)
    planner = CodexCliDynamicPlanner(root=tmp_path, codex_command="codex-test")

    result = planner.plan("Review the auth migration")

    assert result == bundle
    assert calls["args"][:6] == [
        "codex-test",
        "exec",
        "-C",
        str(tmp_path),
        "-s",
        "workspace-write",
    ]
    assert "--output-schema" in calls["args"]
    assert "-a" not in calls["args"]
    assert "Return only JSON" in calls["args"][-1]
    assert calls["kwargs"]["encoding"] == "utf-8"
    assert "plan" in calls["schema"]["properties"]
    assert "procedure" in calls["schema"]["properties"]
    assert "procedure" in calls["schema"]["required"]
    assert "work_units" in calls["schema"]["properties"]["plan"]["required"]


def test_codex_cli_dynamic_planner_raises_user_facing_error_on_cli_failure(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(
        "subprocess.run",
        lambda args, **kwargs: subprocess.CompletedProcess(
            args,
            1,
            stdout="",
            stderr="quota exhausted",
        ),
    )
    planner = CodexCliDynamicPlanner(root=tmp_path, codex_command="codex-test")

    with pytest.raises(RuntimeError, match="quota exhausted"):
        planner.plan("Review the auth migration")
