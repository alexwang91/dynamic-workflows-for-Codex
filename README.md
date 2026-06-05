# dynamic-workflows-for-Codex

External orchestration runtime that recreates Claude-style dynamic workflows for Codex.

The runtime generates typed workflow plans, executes specialist worker tasks through a swappable adapter, persists intermediate state under `.cdw/runs/`, verifies outputs before synthesis, and loops against explicit stop conditions.

Core commands:

```bash
cdw plan "Review this branch"
cdw review "Review this branch with specialist agents"
cdw debug "This test fails 1 in 50 runs"
cdw migrate "Rename User model to Account"
```

## Quickstart

```bash
python -m pip install -e ".[dev]"
python -m pytest
python -m cdw plan "Review this branch" --adapter fake
python -m cdw plan "Review this branch" --save-spec .cdw/specs/review.workflow.json
python -m cdw run .cdw/specs/review.workflow.json --adapter fake
python -m cdw resume <run-id> --adapter fake
python -m cdw migrate "Rename User model to Account" --adapter fake
python -m cdw install-skill
python -m cdw live-smoke
python -m cdw package-plugin --output plugins
```

## What This Recreates

This project recreates the architectural effect of Claude Dynamic Workflows:
task-specific harnesses, isolated workers, runtime-owned state, verification
gates, and synthesis from structured intermediate results.

It does not use Claude's private JavaScript workflow runtime or `ultracode`
trigger.

## Modes

- `fake`: deterministic local worker adapter for development and tests.
- `live`: uses the OpenAI Agents SDK to launch `codex mcp-server` and run
  scoped Codex worker sessions. This requires the optional `[live]`
  dependencies and a working local `codex` command.

## Runtime Artifacts

Each command creates a run directory:

```text
.cdw/runs/<run-id>/state.json
```

The state file is the source of truth for the workflow. It contains the plan,
worker results, verifier results, and final synthesis.

Workflow specs are v2 JSON envelopes with metadata, constraints, acceptance
criteria, and an embedded `WorkflowPlan`. Save them with
`cdw plan --save-spec`, rerun them with `cdw run`, and resume partial runs
from `.cdw/runs/<run-id>/state.json` with `cdw resume`. Older v1 plan-root
spec files remain loadable.

`cdw install-skill` writes a repo-local Codex skill wrapper to
`.agents/skills/dynamic-workflows-for-Codex/SKILL.md`. The skill delegates to
the runtime; it does not own orchestration.

`cdw live-smoke` diagnoses live-mode prerequisites without printing secrets.
Use `cdw live-smoke --execute` only when live dependencies, a working `codex`
CLI, and `OPENAI_API_KEY` are available.

`cdw package-plugin --output plugins` writes a local Codex plugin package at
`plugins/dynamic-workflows-for-codex/` with `.codex-plugin/plugin.json` and a
packaged skill wrapper.
