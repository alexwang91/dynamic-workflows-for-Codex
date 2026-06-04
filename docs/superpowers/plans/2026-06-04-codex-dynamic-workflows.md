# Codex Dynamic Workflows Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python CLI external runtime that recreates Claude-style dynamic workflows for Codex using generated workflow plans, typed state, verification gates, and a Codex MCP worker adapter.

**Architecture:** The runtime keeps workflow state in code and JSON artifacts, not in a chat transcript. The planner creates a typed `WorkflowPlan`; the runtime executes work units through a swappable adapter; fake adapter tests prove control flow before any live Codex MCP call. The live Codex MCP adapter is isolated behind an interface so the MVP stays testable.

**Tech Stack:** Python 3.10+, Pydantic v2, stdlib `argparse`, pytest, optional `openai-agents` for live Codex MCP orchestration.

---

## File Structure

- Create `pyproject.toml`: package metadata, console script, dependencies, pytest config.
- Create `README.md`: quickstart, architecture, limits, fake/live modes.
- Create `.env.example`: optional runtime environment variables.
- Create `src/cdw/__init__.py`: package version.
- Create `src/cdw/__main__.py`: `python -m cdw` entrypoint.
- Create `src/cdw/cli.py`: argparse command handling.
- Create `src/cdw/config.py`: runtime configuration model.
- Create `src/cdw/schemas.py`: Pydantic contracts.
- Create `src/cdw/planner.py`: deterministic MVP planner.
- Create `src/cdw/state.py`: run directory and JSON persistence.
- Create `src/cdw/codex_mcp.py`: worker adapter interface, fake adapter, live adapter placeholder.
- Create `src/cdw/runtime.py`: workflow execution, verification, synthesis, stop conditions.
- Create `src/cdw/prompts/*.md`: prompt templates for future live workers.
- Create `tests/test_schemas.py`: schema validation tests.
- Create `tests/test_planner.py`: planner tests.
- Create `tests/test_state.py`: state persistence tests.
- Create `tests/test_runtime.py`: fake adapter runtime tests.
- Create `tests/test_cli.py`: CLI smoke tests.

## Task 1: Project Scaffold

**Files:**
- Create: `pyproject.toml`
- Create: `README.md`
- Create: `.env.example`
- Create: `src/cdw/__init__.py`
- Create: `src/cdw/__main__.py`
- Create: `tests/test_cli.py`

- [ ] **Step 1: Write the failing CLI import smoke test**

```python
from cdw.cli import build_parser


def test_build_parser_has_core_commands():
    parser = build_parser()

    subcommands = parser._subparsers._group_actions[0].choices

    assert {"plan", "review", "debug"}.issubset(subcommands)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_cli.py::test_build_parser_has_core_commands -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'cdw'`.

- [ ] **Step 3: Create package scaffold**

Create `pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=69", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "codex-dynamic-workflows"
version = "0.1.0"
description = "External orchestration runtime that recreates Claude-style dynamic workflows for Codex."
readme = "README.md"
requires-python = ">=3.10"
dependencies = [
  "pydantic>=2.7",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.2",
]
live = [
  "openai>=1.0",
  "openai-agents>=0.1",
  "python-dotenv>=1.0",
]

[project.scripts]
cdw = "cdw.cli:main"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```

Create `src/cdw/__init__.py`:

```python
__version__ = "0.1.0"
```

Create `src/cdw/__main__.py`:

```python
from cdw.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
```

Create `src/cdw/cli.py`:

```python
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
```

Create minimal `README.md`:

```md
# Codex Dynamic Workflows

External orchestration runtime that recreates Claude-style dynamic workflows for Codex.

The runtime generates typed workflow plans, executes specialist worker tasks through a swappable adapter, persists intermediate state under `.cdw/runs/`, verifies outputs before synthesis, and loops against explicit stop conditions.

MVP commands:

```bash
cdw plan "Review this branch"
cdw review "Review this branch with specialist agents"
cdw debug "This test fails 1 in 50 runs"
```
```

Create `.env.example`:

```env
OPENAI_API_KEY=
CDW_ADAPTER=fake
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_cli.py::test_build_parser_has_core_commands -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml README.md .env.example src/cdw/__init__.py src/cdw/__main__.py src/cdw/cli.py tests/test_cli.py
git commit -m "chore: scaffold cdw package"
```

## Task 2: Typed Workflow Schemas

**Files:**
- Create: `src/cdw/schemas.py`
- Create: `tests/test_schemas.py`

- [ ] **Step 1: Write failing schema tests**

```python
import pytest
from pydantic import ValidationError

from cdw.schemas import WorkflowPlan, WorkUnit


def test_workflow_plan_requires_work_units_and_stop_condition():
    plan = WorkflowPlan(
        command="review",
        request="Review branch",
        pattern="fan-out-and-synthesize",
        work_units=[
            WorkUnit(
                id="security",
                role="security reviewer",
                goal="Find security risks",
                prompt="Review security risks",
                expected_output="Findings with evidence",
            )
        ],
        verification_strategy="adversarial",
        stop_condition="all_required_units_verified",
    )

    assert plan.command == "review"
    assert plan.work_units[0].id == "security"


def test_workflow_plan_rejects_empty_work_units():
    with pytest.raises(ValidationError):
        WorkflowPlan(
            command="review",
            request="Review branch",
            pattern="fan-out-and-synthesize",
            work_units=[],
            verification_strategy="adversarial",
            stop_condition="all_required_units_verified",
        )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_schemas.py -v`

Expected: FAIL with `ModuleNotFoundError` or missing `cdw.schemas`.

- [ ] **Step 3: Implement schema models**

```python
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Command(str, Enum):
    PLAN = "plan"
    REVIEW = "review"
    DEBUG = "debug"


class WorkUnit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    role: str = Field(min_length=1)
    goal: str = Field(min_length=1)
    prompt: str = Field(min_length=1)
    expected_output: str = Field(min_length=1)
    required: bool = True


class WorkflowPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    command: Command
    request: str = Field(min_length=1)
    pattern: str = Field(min_length=1)
    work_units: list[WorkUnit] = Field(min_length=1)
    verification_strategy: str = Field(min_length=1)
    stop_condition: str = Field(min_length=1)
    max_iterations: int = Field(default=1, ge=1, le=10)


class WorkerStatus(str, Enum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class WorkerResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    work_unit_id: str = Field(min_length=1)
    status: WorkerStatus
    summary: str = Field(min_length=1)
    evidence: list[str] = Field(default_factory=list)
    raw_output: str = ""


class VerificationStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"


class VerificationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    work_unit_id: str = Field(min_length=1)
    status: VerificationStatus
    notes: str = Field(min_length=1)


class SynthesisReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["complete", "incomplete"]
    summary: str = Field(min_length=1)
    findings: list[str] = Field(default_factory=list)
    unresolved: list[str] = Field(default_factory=list)


class RunState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str = Field(min_length=1)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    plan: WorkflowPlan
    worker_results: list[WorkerResult] = Field(default_factory=list)
    verification_results: list[VerificationResult] = Field(default_factory=list)
    synthesis: SynthesisReport | None = None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_schemas.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/cdw/schemas.py tests/test_schemas.py
git commit -m "feat: add workflow schemas"
```

## Task 3: Deterministic Planner

**Files:**
- Create: `src/cdw/planner.py`
- Create: `tests/test_planner.py`

- [ ] **Step 1: Write failing planner tests**

```python
from cdw.planner import build_plan


def test_review_plan_uses_fan_out_with_verification():
    plan = build_plan("review", "Review this branch")

    assert plan.command == "review"
    assert plan.pattern == "fan-out-and-synthesize"
    assert plan.verification_strategy == "adversarial"
    assert {unit.id for unit in plan.work_units} >= {"security", "tests", "compatibility", "maintainability"}


def test_debug_plan_uses_hypothesis_loop():
    plan = build_plan("debug", "This test fails 1 in 50 runs")

    assert plan.command == "debug"
    assert plan.pattern == "hypothesis-fan-out-loop"
    assert plan.max_iterations == 3
    assert {unit.id for unit in plan.work_units} >= {"logs", "tests", "code-path", "timing"}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_planner.py -v`

Expected: FAIL with missing `cdw.planner`.

- [ ] **Step 3: Implement planner**

```python
from __future__ import annotations

from cdw.schemas import WorkflowPlan, WorkUnit


def build_plan(command: str, request: str) -> WorkflowPlan:
    if command == "review":
        return _review_plan(request)
    if command == "debug":
        return _debug_plan(request)
    if command == "plan":
        return _planning_plan(request)
    raise ValueError(f"Unsupported command: {command}")


def _review_plan(request: str) -> WorkflowPlan:
    return WorkflowPlan(
        command="review",
        request=request,
        pattern="fan-out-and-synthesize",
        verification_strategy="adversarial",
        stop_condition="all_required_units_verified",
        work_units=[
            WorkUnit(id="security", role="security reviewer", goal="Find security risks", prompt=f"Review security risks for: {request}", expected_output="Security findings with file references and evidence."),
            WorkUnit(id="tests", role="test gap reviewer", goal="Find missing tests", prompt=f"Review test gaps for: {request}", expected_output="Test gap findings with suggested coverage."),
            WorkUnit(id="compatibility", role="compatibility reviewer", goal="Find API or behavior compatibility risks", prompt=f"Review compatibility risks for: {request}", expected_output="Compatibility findings with impacted callers."),
            WorkUnit(id="maintainability", role="maintainability reviewer", goal="Find maintainability risks", prompt=f"Review maintainability for: {request}", expected_output="Maintainability findings with evidence."),
        ],
    )


def _debug_plan(request: str) -> WorkflowPlan:
    return WorkflowPlan(
        command="debug",
        request=request,
        pattern="hypothesis-fan-out-loop",
        verification_strategy="hypothesis-verification",
        stop_condition="supported_hypothesis_or_max_iterations",
        max_iterations=3,
        work_units=[
            WorkUnit(id="logs", role="failure-pattern investigator", goal="Inspect logs and failure patterns", prompt=f"Investigate logs and failure patterns for: {request}", expected_output="Hypotheses tied to observed failure patterns."),
            WorkUnit(id="tests", role="test and fixture investigator", goal="Inspect tests and fixtures", prompt=f"Investigate tests and fixtures for: {request}", expected_output="Hypotheses tied to test setup and fixtures."),
            WorkUnit(id="code-path", role="code path investigator", goal="Trace relevant code paths", prompt=f"Trace code paths for: {request}", expected_output="Hypotheses tied to code paths and state transitions."),
            WorkUnit(id="timing", role="race-condition investigator", goal="Look for timing and concurrency causes", prompt=f"Investigate timing causes for: {request}", expected_output="Hypotheses tied to async, timing, or concurrency."),
        ],
    )


def _planning_plan(request: str) -> WorkflowPlan:
    return WorkflowPlan(
        command="plan",
        request=request,
        pattern="classify-and-act",
        verification_strategy="schema-validation",
        stop_condition="valid_workflow_plan_persisted",
        work_units=[
            WorkUnit(
                id="planner",
                role="workflow planner",
                goal="Create a task-specific workflow plan",
                prompt=f"Create a workflow plan for: {request}",
                expected_output="A valid workflow plan with work units, verification strategy, and stop condition.",
            )
        ],
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_planner.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/cdw/planner.py tests/test_planner.py
git commit -m "feat: add deterministic workflow planner"
```

## Task 4: Run State Persistence

**Files:**
- Create: `src/cdw/state.py`
- Create: `tests/test_state.py`

- [ ] **Step 1: Write failing state tests**

```python
from cdw.planner import build_plan
from cdw.state import create_run_state, load_run_state, save_run_state


def test_save_and_load_run_state(tmp_path):
    plan = build_plan("plan", "Review branch")
    state = create_run_state(plan)

    save_run_state(tmp_path, state)
    loaded = load_run_state(tmp_path, state.run_id)

    assert loaded.run_id == state.run_id
    assert loaded.plan.request == "Review branch"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_state.py -v`

Expected: FAIL with missing `cdw.state`.

- [ ] **Step 3: Implement state persistence**

```python
from __future__ import annotations

import json
import uuid
from pathlib import Path

from cdw.schemas import RunState, WorkflowPlan


def create_run_state(plan: WorkflowPlan) -> RunState:
    return RunState(run_id=uuid.uuid4().hex[:12], plan=plan)


def run_dir(root: Path, run_id: str) -> Path:
    return root / ".cdw" / "runs" / run_id


def save_run_state(root: Path, state: RunState) -> Path:
    directory = run_dir(root, state.run_id)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "state.json"
    tmp_path = directory / "state.json.tmp"
    tmp_path.write_text(state.model_dump_json(indent=2), encoding="utf-8")
    tmp_path.replace(path)
    return path


def load_run_state(root: Path, run_id: str) -> RunState:
    path = run_dir(root, run_id) / "state.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return RunState.model_validate(data)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_state.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/cdw/state.py tests/test_state.py
git commit -m "feat: persist workflow run state"
```

## Task 5: Fake Adapter Runtime

**Files:**
- Create: `src/cdw/codex_mcp.py`
- Create: `src/cdw/runtime.py`
- Create: `tests/test_runtime.py`

- [ ] **Step 1: Write failing runtime tests**

```python
from cdw.codex_mcp import FakeCodexAdapter
from cdw.planner import build_plan
from cdw.runtime import execute_plan


def test_runtime_verifies_before_synthesis(tmp_path):
    plan = build_plan("review", "Review this branch")
    adapter = FakeCodexAdapter()

    state = execute_plan(plan, tmp_path, adapter)

    assert len(state.worker_results) == len(plan.work_units)
    assert len(state.verification_results) == len(plan.work_units)
    assert state.synthesis is not None
    assert state.synthesis.status == "complete"
    assert all(result.status == "passed" for result in state.verification_results)


def test_runtime_marks_incomplete_when_required_worker_fails(tmp_path):
    plan = build_plan("review", "Review this branch")
    adapter = FakeCodexAdapter(fail_work_unit_ids={"security"})

    state = execute_plan(plan, tmp_path, adapter)

    assert state.synthesis is not None
    assert state.synthesis.status == "incomplete"
    assert "security" in state.synthesis.unresolved
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_runtime.py -v`

Expected: FAIL with missing runtime or adapter modules.

- [ ] **Step 3: Implement fake adapter and runtime**

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from cdw.schemas import VerificationResult, VerificationStatus, WorkerResult, WorkerStatus, WorkUnit


class CodexAdapter(Protocol):
    def run_worker(self, work_unit: WorkUnit) -> WorkerResult:
        ...

    def verify_worker_result(self, result: WorkerResult) -> VerificationResult:
        ...


@dataclass
class FakeCodexAdapter:
    fail_work_unit_ids: set[str] = field(default_factory=set)

    def run_worker(self, work_unit: WorkUnit) -> WorkerResult:
        if work_unit.id in self.fail_work_unit_ids:
            return WorkerResult(
                work_unit_id=work_unit.id,
                status=WorkerStatus.FAILED,
                summary=f"{work_unit.id} failed",
                evidence=[],
                raw_output="simulated failure",
            )
        return WorkerResult(
            work_unit_id=work_unit.id,
            status=WorkerStatus.SUCCEEDED,
            summary=f"{work_unit.role} completed {work_unit.goal}",
            evidence=[work_unit.expected_output],
            raw_output=f"fake output for {work_unit.id}",
        )

    def verify_worker_result(self, result: WorkerResult) -> VerificationResult:
        if result.status == WorkerStatus.SUCCEEDED and result.evidence:
            return VerificationResult(
                work_unit_id=result.work_unit_id,
                status=VerificationStatus.PASSED,
                notes="Evidence present.",
            )
        return VerificationResult(
            work_unit_id=result.work_unit_id,
            status=VerificationStatus.FAILED,
            notes="Worker failed or returned no evidence.",
        )
```

```python
from __future__ import annotations

from pathlib import Path

from cdw.codex_mcp import CodexAdapter
from cdw.schemas import SynthesisReport, VerificationStatus, WorkflowPlan, WorkerStatus
from cdw.state import create_run_state, save_run_state


def execute_plan(plan: WorkflowPlan, root: Path, adapter: CodexAdapter):
    state = create_run_state(plan)
    save_run_state(root, state)

    for work_unit in plan.work_units:
        worker_result = adapter.run_worker(work_unit)
        state.worker_results.append(worker_result)
        save_run_state(root, state)

    for worker_result in state.worker_results:
        verification = adapter.verify_worker_result(worker_result)
        state.verification_results.append(verification)
        save_run_state(root, state)

    state.synthesis = _synthesize(state)
    save_run_state(root, state)
    return state


def _synthesize(state) -> SynthesisReport:
    unresolved = [
        result.work_unit_id
        for result in state.worker_results
        if result.status == WorkerStatus.FAILED
    ]
    unresolved.extend(
        verification.work_unit_id
        for verification in state.verification_results
        if verification.status == VerificationStatus.FAILED
        and verification.work_unit_id not in unresolved
    )

    if unresolved:
        return SynthesisReport(
            status="incomplete",
            summary="Workflow completed with unresolved work units.",
            findings=[result.summary for result in state.worker_results],
            unresolved=unresolved,
        )

    return SynthesisReport(
        status="complete",
        summary="Workflow completed after worker execution and verification.",
        findings=[result.summary for result in state.worker_results],
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_runtime.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/cdw/codex_mcp.py src/cdw/runtime.py tests/test_runtime.py
git commit -m "feat: execute workflows with fake adapter"
```

## Task 6: CLI Wiring

**Files:**
- Modify: `src/cdw/cli.py`
- Create: `src/cdw/config.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write failing CLI execution tests**

```python
import json

from cdw.cli import main


def test_plan_command_persists_state(tmp_path, capsys):
    exit_code = main(["plan", "Review branch", "--root", str(tmp_path), "--adapter", "fake"])

    captured = capsys.readouterr()
    state_path = tmp_path / ".cdw" / "runs" / captured.out.strip().split()[-1] / "state.json"

    assert exit_code == 0
    assert state_path.exists()
    data = json.loads(state_path.read_text(encoding="utf-8"))
    assert data["plan"]["command"] == "plan"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_cli.py::test_plan_command_persists_state -v`

Expected: FAIL because CLI does not execute plans.

- [ ] **Step 3: Implement CLI execution**

`src/cdw/config.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RuntimeConfig:
    root: Path
    adapter: str = "fake"
```

Update `src/cdw/cli.py`:

```python
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
```

- [ ] **Step 4: Run CLI tests**

Run: `python -m pytest tests/test_cli.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/cdw/cli.py src/cdw/config.py tests/test_cli.py
git commit -m "feat: wire cli to workflow runtime"
```

## Task 7: Live Codex MCP Adapter Surface

**Files:**
- Modify: `src/cdw/codex_mcp.py`
- Modify: `src/cdw/cli.py`
- Create: `tests/test_codex_mcp.py`

- [ ] **Step 1: Write failing live adapter guard test**

```python
import pytest

from cdw.codex_mcp import LiveCodexAdapter
from cdw.planner import build_plan


def test_live_adapter_has_clear_missing_dependency_error():
    plan = build_plan("plan", "Review branch")
    adapter = LiveCodexAdapter(root=".")

    with pytest.raises(RuntimeError, match="openai-agents"):
        adapter.run_worker(plan.work_units[0])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_codex_mcp.py -v`

Expected: FAIL with missing `LiveCodexAdapter`.

- [ ] **Step 3: Add live adapter dependency boundary**

```python
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from cdw.schemas import VerificationResult, VerificationStatus, WorkerResult, WorkerStatus, WorkUnit


class CodexAdapter(Protocol):
    def run_worker(self, work_unit: WorkUnit) -> WorkerResult:
        ...

    def verify_worker_result(self, result: WorkerResult) -> VerificationResult:
        ...


@dataclass
class LiveCodexAdapter:
    root: str | Path

    def run_worker(self, work_unit: WorkUnit) -> WorkerResult:
        try:
            import agents  # noqa: F401
        except ImportError as exc:
            raise RuntimeError(
                "Live Codex MCP mode requires the optional 'live' dependencies: "
                "pip install 'codex-dynamic-workflows[live]'."
            ) from exc
        raise NotImplementedError("Live Codex MCP execution will be implemented after fake-runtime MVP verification.")

    def verify_worker_result(self, result: WorkerResult) -> VerificationResult:
        if result.status == WorkerStatus.SUCCEEDED and result.evidence:
            return VerificationResult(work_unit_id=result.work_unit_id, status=VerificationStatus.PASSED, notes="Evidence present.")
        return VerificationResult(work_unit_id=result.work_unit_id, status=VerificationStatus.FAILED, notes="Worker failed or returned no evidence.")
```

Keep existing `FakeCodexAdapter` in the same file.

- [ ] **Step 4: Wire live adapter selection**

Update `_build_adapter` in `src/cdw/cli.py`:

```python
def _build_adapter(config: RuntimeConfig):
    if config.adapter == "fake":
        return FakeCodexAdapter()
    from cdw.codex_mcp import LiveCodexAdapter

    return LiveCodexAdapter(root=config.root)
```

- [ ] **Step 5: Run tests**

Run: `python -m pytest tests/test_codex_mcp.py tests/test_cli.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/cdw/codex_mcp.py src/cdw/cli.py tests/test_codex_mcp.py
git commit -m "feat: add live codex adapter boundary"
```

## Task 8: Documentation and Evaluation Checklist

**Files:**
- Modify: `README.md`
- Create: `docs/evaluation.md`
- Create: `src/cdw/prompts/planner.md`
- Create: `src/cdw/prompts/reviewer.md`
- Create: `src/cdw/prompts/debugger.md`
- Create: `src/cdw/prompts/verifier.md`
- Create: `src/cdw/prompts/synthesizer.md`

- [ ] **Step 1: Write documentation**

`docs/evaluation.md`:

```md
# Evaluation Checklist

## Architecture

- Runtime state is stored in `.cdw/runs/<run-id>/state.json`.
- Worker results are structured and persisted before verification.
- Verification results are persisted before synthesis.
- Synthesis reads structured state, not chat transcript history.

## MVP Behavior

- `cdw plan` creates a durable run directory.
- `cdw review` fans out to security, tests, compatibility, and maintainability workers.
- `cdw debug` fans out to logs, tests, code-path, and timing investigators.
- Fake adapter mode works without OpenAI credentials.
- Live adapter mode fails clearly when optional dependencies are missing.
```

Update `README.md` with:

```md
## Quickstart

```bash
python -m pip install -e ".[dev]"
python -m pytest
python -m cdw plan "Review this branch" --adapter fake
```

## What this recreates

This project recreates the architectural effect of Claude Dynamic Workflows: task-specific harnesses, isolated workers, runtime-owned state, verification gates, and synthesis from structured intermediate results.

It does not use Claude's private JavaScript workflow runtime or `ultracode` trigger.

## Modes

- `fake`: deterministic local worker adapter for development and tests.
- `live`: reserved for Codex MCP execution through the optional `openai-agents` dependency.
```

Prompt files should contain concise role instructions matching their filenames.

- [ ] **Step 2: Run documentation-related smoke tests**

Run: `python -m pytest -v`

Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add README.md docs/evaluation.md src/cdw/prompts
git commit -m "docs: explain runtime evaluation"
```

## Task 9: Final Verification

**Files:**
- No new files expected.

- [ ] **Step 1: Run full test suite**

Run: `python -m pytest -v`

Expected: all tests pass.

- [ ] **Step 2: Run CLI smoke**

Run: `python -m cdw plan "Review this branch" --adapter fake`

Expected: exit 0 and prints `run <run-id>`.

- [ ] **Step 3: Inspect run artifact**

Run: `Get-ChildItem -Recurse .cdw | Select-Object -First 20`

Expected: a `.cdw/runs/<run-id>/state.json` file exists.

- [ ] **Step 4: Run design checkpoint**

Read `docs/evaluation.md` and verify:

- Runtime state exists outside chat context.
- Verification happens before synthesis.
- Fake adapter proves the runtime path without live Codex MCP.
- Live adapter boundary is explicit and honest.

- [ ] **Step 5: Commit final cleanup if needed**

If final verification changes files:

```bash
git add <changed-files>
git commit -m "chore: finalize mvp verification"
```

If no files changed, no commit is needed.
