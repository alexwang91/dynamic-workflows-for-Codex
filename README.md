# Dynamic Workflows For Codex

[![Release](https://img.shields.io/badge/release-v0.11-blue)](CHANGELOG.md)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](pyproject.toml)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-85%20passed-brightgreen)](tests)

External dynamic workflow runtime for Codex.

Not a prompt pack. Not a private Claude runtime clone. This is a small,
inspectable runtime that gives Codex the architectural effect of dynamic
workflows: task-specific plans, isolated workers, persisted state, verification
gates, and synthesis from structured intermediate results.

It is built so someone can clone this repo, install it into their own Codex
environment, and run workflows with their own Codex account, login state, API
key, quota, and model access.

## Quickstart

Clone the repo, run tests, check real Codex readiness, and try deterministic
fake mode:

```bash
git clone <repo-url>
cd dynamic-workflows-for-Codex
python -m pip install -e ".[dev]"
python -m pytest
python -m cdw bootstrap
python -m cdw doctor
python -m cdw review "Review this branch" --adapter fake
```

Create and run a reusable workflow spec:

```bash
python -m cdw plan "Review this branch" --planner fake --save-spec .cdw/specs/review.workflow.json
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
python -m cdw bootstrap
codex plugin marketplace add .agents/plugins
```

Then enable `dynamic-workflows-for-codex` in your own Codex environment.
The packaged skill now includes trigger routing, a doctor-first readiness loop,
adapter policy, resume-first behavior, and guardrails against ad hoc prompt
orchestration.

For the full consumer setup, read [docs/consumer-install.md](docs/consumer-install.md).

## What You Get

- `cdw plan`: create a typed workflow plan.
- `cdw plan --planner codex-cli --save-spec`: create a dynamic validated workflow spec through the user's Codex CLI.
- `cdw review`: fan out specialist review workers.
- `cdw debug`: fan out hypothesis investigators.
- `cdw migrate`: create guarded write-heavy migration plans.
- `cdw run`: execute saved workflow specs.
- `cdw resume`: continue an incomplete or human-approved persisted run.
- `cdw bootstrap`: refresh repo-local plugin files and print install next steps.
- `cdw doctor`: check clone readiness without running a real worker.
- `cdw live-smoke`: diagnose live-mode prerequisites.
- `cdw package-plugin`: generate Codex plugin packages.
- `--adapter codex-cli`: run workers through the user's logged-in Codex CLI.

## How It Works

The runtime owns the control plane:

1. Build a typed `WorkflowPlan`.
2. Persist state under `.cdw/runs/<run-id>/state.json`.
3. Dispatch scoped workers through a swappable adapter.
4. Persist worker results before verification.
5. Verify results before synthesis.
6. Synthesize from structured state, not chat history.

Workflow specs are v3 JSON envelopes with metadata, constraints, acceptance
criteria, a procedure graph, and an embedded `WorkflowPlan`. The runtime uses
that procedure graph for `cdw run`: ordered stages, verification gates, failure
behavior, and final artifacts are part of execution, not just documentation.
Older v2 envelopes and v1 plan-root specs still load.

Stages with `manual_review` gates or `require_human` failure behavior pause
before worker execution. The run state records `pending_human_approval`, CLI
reports `waiting for human approval`, and the workflow continues only after:

```bash
python -m cdw resume <run-id> --adapter codex-cli --approve-human-gates
```

Each approval releases only the currently pending stage. Later human-gated
stages pause again.

`cdw plan` now supports planner modes. `static` is the default and preserves the
old fixed planning template. `fake` writes a deterministic multi-stage dynamic
spec for tests and demos. `codex-cli` asks the user's own Codex CLI to design a
full v3 workflow spec using a strict output schema, validates it locally, and
writes it only when `--save-spec` is provided.

## Modes

### Fake

Fake mode is deterministic and needs no credentials:

```bash
python -m cdw review "Review this branch" --adapter fake
```

Use it for tests, demos, and local development.

### Codex CLI

Codex CLI mode uses the user's own `codex exec` login state. It does not require
this repo to store or receive an API key:

```bash
python -m cdw doctor
codex login status
python -m cdw plan "Design a review workflow for this branch" --planner codex-cli --save-spec .cdw/specs/review.workflow.json
python -m cdw review "Review this branch" --adapter codex-cli
python -m cdw run .cdw/specs/review.workflow.json --adapter codex-cli
```

The adapter uses the current `codex exec -C <root> -s <sandbox> <prompt>` shape
and does not pass project-owned API keys or deprecated approval-policy flags.

If `codex` is not on PATH, pass the user's own executable:

```bash
python -m cdw doctor --codex-command /path/to/codex
python -m cdw review "Review this branch" --adapter codex-cli --codex-command /path/to/codex
```

### Live

Live mode uses the OpenAI Agents SDK to launch `codex mcp-server` and run
scoped Codex worker sessions.

```bash
python -m pip install -e ".[live]"
python -m cdw live-smoke --dry-contract
python -m cdw live-smoke
python -m cdw live-smoke --execute
```

Live mode uses the user's own OpenAI/Codex authentication. This repo does not
ship or require the author's API key.

`--dry-contract` prints the Codex MCP tool contract without checking live
dependencies, API keys, or the Codex CLI binary.

If your discovered `codex` command is not directly executable, pass an
override:

```bash
CDW_CODEX_COMMAND=/path/to/codex python -m cdw live-smoke
python -m cdw review "Review this branch" --adapter live --codex-command /path/to/codex
```

## Project Status

Current release: `v0.11`.

- v0.1: MVP runtime with plan/review/debug, fake adapter, live MCP boundary.
- v0.2: workflow specs, resume, guarded migration, skill installer.
- v0.3: live smoke diagnostics, v2 specs, plugin packaging.
- v0.4: cloneable Codex marketplace, command overrides, consumer install docs.
- v0.5: Codex CLI adapter, dry live contract, Windows Codex CLI fallback,
  and clone-user `cdw doctor` diagnostics.
- v0.6: v3 workflow specs with procedure graph stages, gates, triggers,
  failure behavior, v2 backfill compatibility, and staged runtime execution.
- v0.7: hardened plugin skill routing with doctor-first setup, adapter policy,
  resume-first behavior, workflow spec routing, and stronger guardrails.
- v0.8: clone bootstrap command that refreshes repo-local plugin packaging and
  prints marketplace registration plus doctor next steps.
- v0.9: Codex CLI adapter compatibility with current `codex exec` arguments,
  Windows CLI output cleanup, non-zero CLI exits for incomplete workflows, and
  real-smoke-driven codex-cli hardening.
- v0.10: explicit dynamic planner modes for `cdw plan`, including
  `--planner codex-cli` for validated model-generated workflow specs and
  `--planner fake` for deterministic dynamic spec tests.
- v0.11: human approval gates that pause before manual/require-human stages and
  resume only with `--approve-human-gates`.

See [CHANGELOG.md](CHANGELOG.md) for details.

## What This Is Not

- Not Claude's private JavaScript workflow runtime.
- Not the `ultracode` trigger.
- Not a skill-only prompt library.
- Not a shared API-key service.

The plugin and skill are entrypoints. `cdw` owns orchestration.

## License

MIT. See [LICENSE](LICENSE).
