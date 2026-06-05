# Dynamic Workflows For Codex

[![Release](https://img.shields.io/badge/release-v0.4-blue)](CHANGELOG.md)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](pyproject.toml)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-37%20passed-brightgreen)](tests)

External dynamic workflow runtime for Codex.

Not a prompt pack. Not a private Claude runtime clone. This is a small,
inspectable runtime that gives Codex the architectural effect of dynamic
workflows: task-specific plans, isolated workers, persisted state, verification
gates, and synthesis from structured intermediate results.

It is built so someone can clone this repo, install it into their own Codex
environment, and run workflows with their own Codex account, API key, quota,
and model access.

## Quickstart

Clone the repo and run deterministic fake mode:

```bash
git clone <repo-url>
cd dynamic-workflows-for-Codex
python -m pip install -e ".[dev]"
python -m pytest
python -m cdw review "Review this branch" --adapter fake
```

Create and run a reusable workflow spec:

```bash
python -m cdw plan "Review this branch" --save-spec .cdw/specs/review.workflow.json
python -m cdw run .cdw/specs/review.workflow.json --adapter fake
python -m cdw resume <run-id> --adapter fake
```

Create a guarded migration plan:

```bash
python -m cdw migrate "Rename User model to Account" --adapter fake
```

## Install Into Codex

This repo includes a cloneable Codex plugin marketplace:

```text
.agents/plugins/marketplace.json
.agents/plugins/plugins/dynamic-workflows-for-codex/
```

If your Codex install needs explicit marketplace registration:

```bash
codex plugin marketplace add .agents/plugins
```

Then enable `dynamic-workflows-for-codex` in your own Codex environment.

For the full consumer setup, read [docs/consumer-install.md](docs/consumer-install.md).

## What You Get

- `cdw plan`: create a typed workflow plan.
- `cdw review`: fan out specialist review workers.
- `cdw debug`: fan out hypothesis investigators.
- `cdw migrate`: create guarded write-heavy migration plans.
- `cdw run`: execute saved workflow specs.
- `cdw resume`: continue an incomplete persisted run.
- `cdw live-smoke`: diagnose live-mode prerequisites.
- `cdw package-plugin`: generate Codex plugin packages.

## How It Works

The runtime owns the control plane:

1. Build a typed `WorkflowPlan`.
2. Persist state under `.cdw/runs/<run-id>/state.json`.
3. Dispatch scoped workers through a swappable adapter.
4. Persist worker results before verification.
5. Verify results before synthesis.
6. Synthesize from structured state, not chat history.

Workflow specs are v2 JSON envelopes with metadata, constraints, acceptance
criteria, and an embedded `WorkflowPlan`. Older v1 plan-root specs still load.

## Modes

### Fake

Fake mode is deterministic and needs no credentials:

```bash
python -m cdw review "Review this branch" --adapter fake
```

Use it for tests, demos, and local development.

### Live

Live mode uses the OpenAI Agents SDK to launch `codex mcp-server` and run
scoped Codex worker sessions.

```bash
python -m pip install -e ".[live]"
python -m cdw live-smoke
python -m cdw live-smoke --execute
```

Live mode uses the user's own OpenAI/Codex authentication. This repo does not
ship or require the author's API key.

If your discovered `codex` command is not directly executable, pass an
override:

```bash
CDW_CODEX_COMMAND=/path/to/codex python -m cdw live-smoke
python -m cdw review "Review this branch" --adapter live --codex-command /path/to/codex
```

## Project Status

Current release: `v0.4`.

- v0.1: MVP runtime with plan/review/debug, fake adapter, live MCP boundary.
- v0.2: workflow specs, resume, guarded migration, skill installer.
- v0.3: live smoke diagnostics, v2 specs, plugin packaging.
- v0.4: cloneable Codex marketplace, command overrides, consumer install docs.

See [CHANGELOG.md](CHANGELOG.md) for details.

## What This Is Not

- Not Claude's private JavaScript workflow runtime.
- Not the `ultracode` trigger.
- Not a skill-only prompt library.
- Not a shared API-key service.

The plugin and skill are entrypoints. `cdw` owns orchestration.

## License

MIT. See [LICENSE](LICENSE).
