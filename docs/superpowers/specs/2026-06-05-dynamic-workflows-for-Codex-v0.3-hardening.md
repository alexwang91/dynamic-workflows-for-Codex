# dynamic-workflows-for-Codex v0.3 Hardening Design

## Goal

Harden the v0.2 runtime so it can be diagnosed against real live-mode prerequisites, express reusable workflow specs beyond a bare `WorkflowPlan`, and package the runtime entrypoint as a Codex plugin bundle.

## Context

v0.2 established the baseline:

- `master` contains v0.2 and is tagged `v0.2`.
- Runtime state remains outside chat context in `.cdw/runs/<run-id>/state.json`.
- Workflow specs can be saved and run.
- Incomplete runs can be resumed.
- `migrate` creates a guarded migration workflow.
- `install-skill` writes a repo-local skill wrapper.

The next gap is operational hardening. We need clear live-mode diagnostics, richer specs for sharing/reuse, and a real plugin package shape.

## Requirements

### Live Smoke

- Add `cdw live-smoke`.
- The command reports live-mode prerequisites without leaking secrets:
  - `agents` import availability.
  - `openai` import availability.
  - `codex` command discovery.
  - `codex --version` executable check.
  - `OPENAI_API_KEY` presence when an actual live run is requested.
- The command must catch permission and process-launch errors cleanly. On this machine, `codex --version` currently fails with Access denied; this should be reported as a failed check, not a traceback.
- Add `--execute` for an actual minimal live worker run after prerequisites pass.
- Default mode is preflight-only so CI and local development can run it without credentials.
- Return exit code `0` only when required checks for the selected mode pass.

### Stronger Workflow Spec Expression

- Save new workflow specs as a v2 envelope while keeping old v1 plan-root specs loadable.
- v2 envelope shape:
  - `schema_version: "2"`
  - `kind: "codex.dynamic-workflow"`
  - `metadata`
  - `constraints`
  - `acceptance_criteria`
  - `plan`
- `cdw run <workflow-spec>` continues to execute the embedded `WorkflowPlan`.
- `load_workflow_spec()` remains backward compatible for existing callers by returning a `WorkflowPlan`.
- Add a second loader for callers that need the full envelope.
- Migration specs default to guarded/write-heavy constraints. Review/debug/plan specs default to read-only constraints.

### Plugin Packaging

- Add `cdw package-plugin`.
- The command writes a repo-local plugin package by default:
  - `plugins/dynamic-workflows-for-codex/.codex-plugin/plugin.json`
  - `plugins/dynamic-workflows-for-codex/skills/dynamic-workflows-for-codex/SKILL.md`
- Plugin manifest uses normalized lowercase plugin name `dynamic-workflows-for-codex`.
- The packaged skill delegates orchestration to `cdw`; it must not replace runtime control with free-form prompting.
- Validate the package shape in tests and with the plugin-creator validator when available.

## Non-Goals

- Do not publish to a marketplace in v0.3.
- Do not mutate the user's global `~/.agents/plugins/marketplace.json` by default.
- Do not require live credentials for normal unit tests.
- Do not auto-install `openai`, `openai-agents`, or Codex CLI.
- Do not perform write-heavy migrations automatically.

## Acceptance Checks

- `python -m pytest -v` passes.
- `python -m cdw live-smoke` exits cleanly and reports failed prerequisites in this environment.
- `python -m cdw plan "Review this branch" --save-spec .cdw/specs/review-v2.workflow.json` writes a v2 envelope.
- `python -m cdw run .cdw/specs/review-v2.workflow.json --adapter fake` still runs.
- A handcrafted v1 plan-root spec still loads and runs.
- `python -m cdw package-plugin --output .cdw/plugin-smoke` writes a plugin package with a valid `.codex-plugin/plugin.json`.
