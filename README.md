# dynamic-workflows-for-Codex

External orchestration runtime that recreates Claude-style dynamic workflows for Codex.

The runtime generates typed workflow plans, executes specialist worker tasks through a swappable adapter, persists intermediate state under `.cdw/runs/`, verifies outputs before synthesis, and loops against explicit stop conditions.

MVP commands:

```bash
cdw plan "Review this branch"
cdw review "Review this branch with specialist agents"
cdw debug "This test fails 1 in 50 runs"
```

## Quickstart

```bash
python -m pip install -e ".[dev]"
python -m pytest
python -m cdw plan "Review this branch" --adapter fake
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
