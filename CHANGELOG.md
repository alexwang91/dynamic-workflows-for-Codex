# Changelog

All notable changes to `dynamic-workflows-for-Codex` are documented here.

## v0.4 - 2026-06-05

- Added cloneable repo-local Codex plugin marketplace under `.agents/plugins/`.
- Added consumer install guide for users cloning the repository.
- Added configurable Codex command resolution through `--codex-command` and `CDW_CODEX_COMMAND`.
- Wired configured Codex commands into live smoke diagnostics and live MCP adapter execution.
- Hardened Windows live-smoke diagnostics for WindowsApps access-denied and decode errors.
- Bumped package and plugin metadata to `0.4.0`.

## v0.3 - 2026-06-05

- Added `cdw live-smoke` for live-mode prerequisite diagnostics.
- Added v2 workflow spec envelopes with metadata, constraints, acceptance criteria, and embedded plans.
- Preserved compatibility with v1 plan-root workflow specs.
- Added `cdw package-plugin` for local Codex plugin package generation.

## v0.2 - 2026-06-05

- Added reusable workflow spec save/run support.
- Added resumable runs with `cdw resume`.
- Added guarded migration workflow planning with ownership boundaries and patch-review gates.
- Added repo-local Codex skill installer.
- Fixed transient Windows state-file replacement failures.

## v0.1 - 2026-06-05

- Established the MVP external runtime architecture.
- Added typed workflow plans, durable run state, worker dispatch, verification, and synthesis.
- Added fake adapter for deterministic development and tests.
- Added live Codex MCP adapter boundary with dependency error handling.
- Added initial plan/review/debug CLI commands.
