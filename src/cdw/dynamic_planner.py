from __future__ import annotations

import json
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from cdw.codex_cli import _clean_codex_output
from cdw.planner import build_plan
from cdw.schemas import (
    WorkflowProcedure,
    WorkflowPlan,
    WorkflowSpecBundle,
    WorkflowSpecConstraints,
    WorkflowSpecMetadata,
    WorkflowStage,
    WorkUnit,
)
from cdw.workflow_spec import build_workflow_spec_bundle


PLANNER_CHOICES = ("static", "fake", "codex-cli")


def build_dynamic_workflow_spec(
    request: str,
    planner: str,
    root: str | Path,
    codex_command: str = "codex",
) -> WorkflowSpecBundle:
    if planner == "static":
        return build_workflow_spec_bundle(build_plan("plan", request))
    if planner == "fake":
        return _fake_dynamic_workflow_spec(request)
    if planner == "codex-cli":
        return CodexCliDynamicPlanner(root=root, codex_command=codex_command).plan(
            request
        )
    raise ValueError(f"Unsupported dynamic planner: {planner}")


def parse_dynamic_planner_output(output: str) -> WorkflowSpecBundle:
    try:
        data = json.loads(_extract_json_text(output))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"dynamic planner returned invalid JSON: {exc}") from exc

    try:
        return WorkflowSpecBundle.model_validate(data)
    except ValidationError as exc:
        raise RuntimeError(
            f"dynamic planner returned invalid workflow spec: {exc}"
        ) from exc


@dataclass
class CodexCliDynamicPlanner:
    root: str | Path
    sandbox: str = "workspace-write"
    timeout_seconds: int = 3600
    codex_command: str = "codex"

    def plan(self, request: str) -> WorkflowSpecBundle:
        with tempfile.TemporaryDirectory() as temp_dir:
            schema_path = Path(temp_dir) / "workflow-spec.schema.json"
            schema_path.write_text(
                json.dumps(_workflow_spec_output_schema(), indent=2),
                encoding="utf-8",
            )
            args = [
                self.codex_command,
                "exec",
                "-C",
                str(Path(self.root)),
                "-s",
                self.sandbox,
                "--output-schema",
                str(schema_path),
                _dynamic_planner_prompt(request),
            ]
            try:
                completed = subprocess.run(
                    args,
                    capture_output=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=self.timeout_seconds,
                    check=False,
                )
            except (OSError, subprocess.TimeoutExpired) as exc:
                raise RuntimeError(
                    f"Codex CLI dynamic planner could not run codex exec: {exc}"
                ) from exc

        output = _clean_codex_output(completed.stdout or completed.stderr)
        if completed.returncode != 0:
            message = output or f"codex exec exited with {completed.returncode}"
            raise RuntimeError(f"Codex CLI dynamic planner failed: {message}")
        if not output:
            raise RuntimeError("Codex CLI dynamic planner returned no output.")
        return parse_dynamic_planner_output(output)


def _fake_dynamic_workflow_spec(request: str) -> WorkflowSpecBundle:
    plan = WorkflowPlan(
        command="plan",
        request=request,
        pattern="dynamic-sequence-and-review",
        verification_strategy="stage-gated-schema-and-risk-review",
        stop_condition="dynamic_workflow_spec_validated",
        work_units=[
            WorkUnit(
                id="context",
                role="context mapper",
                goal="Identify task scope, constraints, and likely affected areas",
                prompt=f"Map context for dynamic workflow request: {request}",
                expected_output="Scope summary, affected areas, constraints, and unknowns.",
            ),
            WorkUnit(
                id="workflow",
                role="workflow designer",
                goal="Design staged worker roles and verification gates",
                prompt=f"Design a staged dynamic workflow for: {request}",
                expected_output="Ordered worker roles, prompts, gates, and final artifacts.",
            ),
            WorkUnit(
                id="risk-review",
                role="workflow risk reviewer",
                goal="Challenge missing gates, unsafe writes, and ambiguous outputs",
                prompt=f"Review dynamic workflow risks for: {request}",
                expected_output="Risk findings and gate improvements.",
            ),
        ],
    )
    return WorkflowSpecBundle(
        schema_version="3",
        metadata=WorkflowSpecMetadata(
            name=f"dynamic plan: {request}",
            description=request,
            created_by="cdw-dynamic-planner",
        ),
        constraints=WorkflowSpecConstraints(write_policy="read-only"),
        acceptance_criteria=[
            "dynamic_workflow_spec_validated",
            "all_required_stages_verified",
        ],
        procedure=WorkflowProcedure(
            mode="sequence",
            triggers=["plan", "dynamic workflow"],
            stages=[
                WorkflowStage(
                    id="context",
                    purpose="Map scope and constraints before designing workers",
                    work_unit_ids=["context"],
                    produces=["scope summary"],
                    gate="all_required_verified",
                    on_failure="stop",
                    write_policy="read-only",
                ),
                WorkflowStage(
                    id="workflow-design",
                    purpose="Design and challenge the dynamic workflow",
                    work_unit_ids=["workflow", "risk-review"],
                    depends_on=["context"],
                    consumes=["scope summary"],
                    produces=["validated workflow spec", "risk findings"],
                    gate="all_required_verified",
                    on_failure="stop",
                    write_policy="read-only",
                ),
            ],
            final_artifacts=["validated workflow spec", "synthesis report"],
        ),
        plan=plan,
    )


def _extract_json_text(output: str) -> str:
    stripped = output.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", stripped, re.DOTALL)
    if fenced is not None:
        return fenced.group(1).strip()
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start != -1 and end != -1 and end > start:
        return stripped[start : end + 1]
    return stripped


def _dynamic_planner_prompt(request: str) -> str:
    return (
        "Return only JSON for a cdw WorkflowSpecBundle. Do not include Markdown.\n"
        "The JSON must validate against this shape:\n"
        "- schema_version: \"3\"\n"
        "- kind: \"codex.dynamic-workflow\"\n"
        "- metadata: name, description, created_by\n"
        "- constraints: write_policy, allowed_paths, forbidden_paths, requires_human_approval, requires_write_contract\n"
        "- acceptance_criteria: string array\n"
        "- procedure: mode, triggers, stages, final_artifacts\n"
        "- procedure.stages: id, purpose, work_unit_ids, depends_on, consumes, produces, gate, on_failure, write_policy\n"
        "- plan: schema_version, command, request, pattern, work_units, verification_strategy, stop_condition, max_iterations\n"
        "Use plan.command = \"plan\". Every work unit id must appear exactly once in procedure stages.\n"
        "Stage dependencies must reference earlier stages. Consumed artifacts must be produced by declared dependency stages.\n"
        "Default to read-only unless the request clearly requires guarded or write-heavy planning.\n"
        "Use manual_review or require_human gates for guarded or write-heavy stages.\n"
        "Set requires_write_contract=true when guarded/write-heavy stages must emit WRITE_CONTRACT JSON.\n"
        f"Request: {request}\n"
    )


def _workflow_spec_output_schema() -> dict:
    string_array = {"type": "array", "items": {"type": "string"}}
    work_unit = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "id": {"type": "string"},
            "role": {"type": "string"},
            "goal": {"type": "string"},
            "prompt": {"type": "string"},
            "expected_output": {"type": "string"},
            "required": {"type": "boolean"},
        },
        "required": [
            "id",
            "role",
            "goal",
            "prompt",
            "expected_output",
            "required",
        ],
    }
    stage = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "id": {"type": "string"},
            "purpose": {"type": "string"},
            "work_unit_ids": string_array,
            "depends_on": string_array,
            "consumes": string_array,
            "produces": string_array,
            "gate": {
                "type": "string",
                "enum": ["all_required_verified", "any_verified", "manual_review"],
            },
            "on_failure": {
                "type": "string",
                "enum": ["stop", "continue", "require_human"],
            },
            "write_policy": {
                "type": "string",
                "enum": ["read-only", "guarded", "write-heavy"],
            },
        },
        "required": [
            "id",
            "purpose",
            "work_unit_ids",
            "depends_on",
            "consumes",
            "produces",
            "gate",
            "on_failure",
            "write_policy",
        ],
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "schema_version": {"type": "string", "enum": ["3"]},
            "kind": {"type": "string", "enum": ["codex.dynamic-workflow"]},
            "metadata": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "created_by": {"type": "string"},
                },
                "required": ["name", "description", "created_by"],
            },
            "constraints": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "write_policy": {
                        "type": "string",
                        "enum": ["read-only", "guarded", "write-heavy"],
                    },
                    "allowed_paths": string_array,
                    "forbidden_paths": string_array,
                    "requires_human_approval": {"type": "boolean"},
                    "requires_write_contract": {"type": "boolean"},
                },
                "required": [
                    "write_policy",
                    "allowed_paths",
                    "forbidden_paths",
                    "requires_human_approval",
                    "requires_write_contract",
                ],
            },
            "acceptance_criteria": string_array,
            "procedure": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "mode": {
                        "type": "string",
                        "enum": ["single-stage", "fan-out", "sequence", "guarded"],
                    },
                    "triggers": string_array,
                    "stages": {"type": "array", "items": stage},
                    "final_artifacts": string_array,
                },
                "required": ["mode", "triggers", "stages", "final_artifacts"],
            },
            "plan": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "schema_version": {"type": "string"},
                    "command": {"type": "string", "enum": ["plan"]},
                    "request": {"type": "string"},
                    "pattern": {"type": "string"},
                    "work_units": {"type": "array", "items": work_unit},
                    "verification_strategy": {"type": "string"},
                    "stop_condition": {"type": "string"},
                    "max_iterations": {"type": "integer", "minimum": 1, "maximum": 10},
                },
                "required": [
                    "schema_version",
                    "command",
                    "request",
                    "pattern",
                    "work_units",
                    "verification_strategy",
                    "stop_condition",
                    "max_iterations",
                ],
            },
        },
        "required": [
            "schema_version",
            "kind",
            "metadata",
            "constraints",
            "acceptance_criteria",
            "procedure",
            "plan",
        ],
    }
