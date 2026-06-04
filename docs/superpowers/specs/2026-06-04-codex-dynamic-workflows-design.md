---
title: dynamic-workflows-for-Codex Design
date: 2026-06-04
status: approved-for-planning
---

# dynamic-workflows-for-Codex Design

## 1. Product Goal

Build `dynamic-workflows-for-Codex`, a GitHub-shareable external orchestration runtime that recreates the architectural effect of Claude Code dynamic workflows for Codex.

This project is not a prompt library and not a Codex skill-only workflow. It is a runtime that:

- Generates task-specific executable workflow plans.
- Runs specialist Codex agents through the Codex MCP server.
- Stores intermediate results outside the main conversation context.
- Enforces verification gates before synthesis.
- Loops until explicit stop conditions are met.
- Preserves workflow state so runs are inspectable and resumable.

The intended user experience is:

```bash
cdw plan "Review this branch for security, test gaps, and API compatibility"
cdw review "Review this branch with specialist agents"
cdw debug "This test fails about 1 in 50 runs"
```

## 2. What "Recreate Claude Dynamic Workflows" Means

The target is behavior and architecture equivalence, not private implementation equivalence.

We can recreate:

- Dynamic task classification.
- Task-specific harness generation.
- Fan-out-and-synthesize.
- Adversarial verification.
- Generate-and-filter.
- Tournament selection.
- Loop-until-done.
- Isolated worker context.
- State held by the runtime, not by a single chat context.
- Final synthesis from structured intermediate outputs.

We cannot directly recreate:

- Claude Code's private JavaScript workflow runtime.
- Claude's `ultracode` trigger and internal runtime hooks.
- Any private Claude Code subagent control API.

Our equivalent implementation:

```text
Python CLI
  -> OpenAI Agents SDK orchestration
  -> Codex MCP server as worker execution surface
  -> state files under .cdw/runs/<run-id>/
  -> generated workflow spec as executable runtime input
```

The runtime owns the control plane. Codex sessions are execution workers.

## 3. MVP Scope

### In Scope

First release commands:

- `cdw plan`: produce and persist a workflow plan without executing all worker tasks.
- `cdw review`: run a read-heavy multi-agent code review workflow.
- `cdw debug`: run a hypothesis-driven debugging workflow.

Core workflow patterns:

- Classify-and-act.
- Fan-out-and-synthesize.
- Adversarial verification.
- Loop-until-done with bounded iteration limits.

Core runtime behavior:

- Start or connect to `codex mcp-server`.
- Dispatch isolated Codex MCP sessions with scoped prompts.
- Persist every run to `.cdw/runs/<run-id>/`.
- Persist plan, worker tasks, worker outputs, verifier outputs, final synthesis, and run metadata.
- Support a dry-run/mock adapter so tests do not require live Codex MCP calls.

### Out of Scope for MVP

- Full plugin marketplace distribution.
- Full Codex skill packaging.
- Write-heavy migration workflows that let parallel agents edit the same codebase.
- Arbitrary JavaScript workflow execution.
- Distributed execution across machines.
- Cloud job management.
- UI dashboard.

The MVP should leave clean extension points for these later.

## 4. Architecture

### Components

```text
src/cdw/
  cli.py
  config.py
  orchestrator.py
  planner.py
  runtime.py
  codex_mcp.py
  agents.py
  state.py
  schemas.py
  prompts/
    planner.md
    reviewer.md
    debugger.md
    verifier.md
    synthesizer.md
tests/
docs/
```

### Responsibilities

`cli.py`

- Owns command parsing and user-facing output.
- Calls the orchestrator.
- Does not contain workflow logic.

`config.py`

- Reads defaults for model, reasoning effort, sandbox, approval policy, max workers, and max iterations.
- Allows command-line overrides.

`schemas.py`

- Defines structured Pydantic models for workflow plans, work units, agent outputs, verification reports, synthesis reports, and run state.
- Provides the contract between planner, runtime, workers, verifiers, and synthesizer.

`planner.py`

- Converts a user request into a task-specific `WorkflowPlan`.
- Selects workflow pattern, worker roles, verification strategy, stop condition, and output schema.
- Supports deterministic rule-based planning first, with an LLM planning adapter added behind an interface.

`runtime.py`

- Executes a `WorkflowPlan`.
- Owns fan-out, barriers, verification passes, loop conditions, and synthesis.
- Keeps intermediate state in `.cdw/runs/<run-id>/`.

`codex_mcp.py`

- Wraps the Codex MCP tool calls.
- Starts Codex sessions with scoped prompts.
- Continues sessions when needed.
- Provides a fake adapter for tests.

`agents.py`

- Defines reusable agent role prompts and task templates.
- Keeps planner/runtime logic separate from role instructions.

`state.py`

- Creates run directories.
- Writes JSON artifacts atomically.
- Loads previous run state for inspection or future resume support.

## 5. Data Flow

```text
User command
  -> CLI parses command
  -> config resolves runtime options
  -> planner creates WorkflowPlan
  -> state persists plan
  -> runtime executes work units
  -> Codex MCP adapter starts worker sessions
  -> workers return structured outputs
  -> verifier work units check outputs against rubrics
  -> runtime evaluates stop condition
  -> synthesizer produces final report
  -> state persists final artifacts
```

The main process should never rely on a growing chat transcript as the source of truth. The source of truth is the typed run state.

## 6. Workflow Patterns

### Review Workflow

Pattern:

- Classify review scope.
- Fan out to specialist workers.
- Verify findings.
- Synthesize by severity and evidence.

Initial specialist roles:

- Security reviewer.
- Test gap reviewer.
- Compatibility reviewer.
- Maintainability reviewer.

Stop condition:

- All required reviewers return structured findings.
- Verifier pass completes.
- No required verifier reports unresolved schema or evidence failures.

### Debug Workflow

Pattern:

- Generate independent hypotheses.
- Fan out evidence collectors.
- Verify each hypothesis.
- Loop until no new plausible hypothesis appears or max iterations is reached.

Initial specialist roles:

- Logs and failure-pattern investigator.
- Test and fixture investigator.
- Code path investigator.
- Race-condition and timing investigator.

Stop condition:

- At least one hypothesis is supported by evidence and a falsification path.
- Or max iterations is reached with a clear inconclusive report.

### Plan Workflow

Pattern:

- Classify task.
- Generate work units.
- Generate verification contract.
- Persist the plan.

Stop condition:

- Valid `WorkflowPlan` persisted.
- Plan passes schema validation.

## 7. Error Handling

Runtime errors must be visible and recoverable.

- If Codex MCP is unavailable, fail with setup guidance and keep the run plan.
- If a worker fails, persist its failure as a structured worker result.
- If a verifier fails, mark synthesis as blocked unless the workflow allows partial synthesis.
- If output is malformed, retry once with a repair prompt, then persist a schema failure.
- If max iterations are reached, return an explicit incomplete result rather than claiming completion.

## 8. Security and Safety Boundaries

MVP workflows are read-heavy by default.

- Worker prompts must describe allowed action scope.
- Parallel write-heavy workflows are disabled in MVP.
- Default Codex MCP calls should use `sandbox: workspace-write` only when execution needs workspace access.
- `approval-policy: never` may be supported for noninteractive workflows, but should be visible in config and docs.
- Untrusted inputs should be separated from high-privilege actions in later triage workflows.

## 9. Testing Strategy

Use test-driven development.

Unit tests:

- Schema validation.
- Planner output for `plan`, `review`, and `debug`.
- State persistence and loading.
- Runtime behavior with fake Codex adapter.
- Stop condition evaluation.
- Malformed worker-output repair path.

Integration tests:

- CLI smoke tests with fake adapter.
- One optional live Codex MCP smoke test, skipped unless environment variables enable it.

Manual verification:

- Run `cdw plan` in a sample repo.
- Run `cdw review` with fake adapter and inspect `.cdw/runs/<run-id>/`.
- Run a live Codex MCP smoke when credentials and local Codex CLI are available.

## 10. Evaluation Checkpoints

The project should be evaluated continuously at phase boundaries.

### Design Evaluation

- Does the design preserve the key dynamic workflow principle: runtime state outside chat context?
- Does the design avoid pretending a Codex skill alone can control subagents?
- Are MVP boundaries narrow enough to finish?

### Implementation Evaluation

- Are modules small and purpose-specific?
- Are interfaces typed and testable?
- Can the Codex MCP adapter be replaced by a fake adapter?
- Does the runtime own control flow instead of hiding orchestration inside prompts?

### Behavior Evaluation

- Does each command create a durable run directory?
- Are worker outputs structured?
- Does verification happen before synthesis?
- Does the runtime stop only when the declared stop condition is met?

### Completion Evaluation

- Do tests pass?
- Does the README explain setup and limits honestly?
- Does a user understand the difference between this runtime and a Codex skill?
- Is there a clear path to plugin/skill packaging after MVP?

## 11. Distribution Plan

MVP distribution:

- Python package with a `cdw` console script.
- GitHub README with quickstart and architecture.
- `.env.example` for OpenAI API key configuration.

Future distribution:

- Codex skill that tells Codex when to use `cdw`.
- Codex plugin packaging for the skill and optional MCP configuration.
- Workflow template marketplace.

## 12. Risks

### Risk: The runtime becomes only a prompt wrapper.

Mitigation:

- Keep control flow, state, barriers, verifier passes, and loop conditions in code.

### Risk: Live Codex MCP behavior is hard to test.

Mitigation:

- Design an adapter interface from the start.
- Make fake adapter tests the default.
- Keep live MCP smoke tests optional.

### Risk: Parallel write-heavy workflows corrupt the workspace.

Mitigation:

- Keep MVP read-heavy.
- Add write-heavy support only after worktree isolation is designed.

### Risk: Users expect exact Claude feature parity.

Mitigation:

- State that this recreates architecture and behavior, not Claude private runtime hooks.

## 13. Open Questions for Later

- Should generated workflow specs be Python modules, YAML files, or JSON state machines?
- Should the first write-heavy workflow be `migrate`, `fix`, or `implement`?
- Should plugin packaging ship in v0.2 or v0.3?
- Should live Codex MCP smoke tests run in CI or remain local-only?

For MVP, use JSON/Pydantic workflow plans and keep generated executable Python/YAML workflow authoring for a later milestone.
