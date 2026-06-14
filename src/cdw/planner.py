from __future__ import annotations

from cdw.schemas import WorkflowPlan, WorkUnit


def build_plan(command: str, request: str) -> WorkflowPlan:
    if command == "review":
        return _review_plan(request)
    if command == "debug":
        return _debug_plan(request)
    if command == "plan":
        return _planning_plan(request)
    if command == "migrate":
        return _migration_plan(request)
    raise ValueError(f"Unsupported command: {command}")


def _review_plan(request: str) -> WorkflowPlan:
    return WorkflowPlan(
        command="review",
        request=request,
        pattern="fan-out-and-synthesize",
        verification_strategy="adversarial",
        stop_condition="all_required_units_verified",
        work_units=[
            WorkUnit(
                id="security",
                role="security reviewer",
                goal="Find security risks",
                prompt=f"Review security risks for: {request}",
                expected_output="Security findings with file references and evidence.",
            ),
            WorkUnit(
                id="tests",
                role="test gap reviewer",
                goal="Find missing tests",
                prompt=f"Review test gaps for: {request}",
                expected_output="Test gap findings with suggested coverage.",
            ),
            WorkUnit(
                id="compatibility",
                role="compatibility reviewer",
                goal="Find API or behavior compatibility risks",
                prompt=f"Review compatibility risks for: {request}",
                expected_output="Compatibility findings with impacted callers.",
            ),
            WorkUnit(
                id="maintainability",
                role="maintainability reviewer",
                goal="Find maintainability risks",
                prompt=f"Review maintainability for: {request}",
                expected_output="Maintainability findings with evidence.",
            ),
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
            WorkUnit(
                id="logs",
                role="failure-pattern investigator",
                goal="Inspect logs and failure patterns",
                prompt=f"Investigate logs and failure patterns for: {request}",
                expected_output="Hypotheses tied to observed failure patterns.",
            ),
            WorkUnit(
                id="tests",
                role="test and fixture investigator",
                goal="Inspect tests and fixtures",
                prompt=f"Investigate tests and fixtures for: {request}",
                expected_output="Hypotheses tied to test setup and fixtures.",
            ),
            WorkUnit(
                id="code-path",
                role="code path investigator",
                goal="Trace relevant code paths",
                prompt=f"Trace code paths for: {request}",
                expected_output="Hypotheses tied to code paths and state transitions.",
            ),
            WorkUnit(
                id="timing",
                role="race-condition investigator",
                goal="Look for timing and concurrency causes",
                prompt=f"Investigate timing causes for: {request}",
                expected_output="Hypotheses tied to async, timing, or concurrency.",
            ),
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
                expected_output=(
                    "A valid workflow plan with work units, verification "
                    "strategy, and stop condition."
                ),
            )
        ],
    )


def _migration_plan(request: str) -> WorkflowPlan:
    return WorkflowPlan(
        command="migrate",
        request=request,
        pattern="guarded-migration",
        verification_strategy="patch-review",
        stop_condition="migration_review_complete",
        work_units=[
            WorkUnit(
                id="inventory",
                role="migration inventory planner",
                goal="Find affected symbols, files, and callers",
                prompt=(
                    "Create a read-only migration inventory for: "
                    f"{request}. ownership: identify affected modules, owners, "
                    "callers, generated files, and files that should remain untouched."
                ),
                expected_output=(
                    "Affected symbols and files, with ownership boundaries and "
                    "areas excluded from the migration."
                ),
            ),
            WorkUnit(
                id="patch-plan",
                role="migration patch planner",
                goal="Propose bounded file ownership slices",
                prompt=(
                    "Propose a guarded patch plan for: "
                    f"{request}. ownership: split the migration into bounded "
                    "file/module slices and name the checks required before edits. "
                    "Include a machine-readable WRITE_CONTRACT JSON section with "
                    'a "paths" array before any later write-heavy phase can proceed.'
                ),
                expected_output=(
                    "Ordered patch slices, ownership boundaries, risk notes, and "
                    'required tests for each slice, plus WRITE_CONTRACT with "paths", '
                    '"action", "reason", and planned "checks".'
                ),
            ),
            WorkUnit(
                id="verification",
                role="migration verifier",
                goal="Review migration risks before write-heavy work",
                prompt=(
                    "Verify the proposed migration approach for: "
                    f"{request}. ownership: challenge risky slices, missing tests, "
                    "compatibility breaks, missing WRITE_CONTRACT paths, and any "
                    "area needing human approval."
                ),
                expected_output=(
                    "Patch-review findings, migration risks, required tests, and "
                    "approval gates before write-heavy execution."
                ),
            ),
        ],
    )
