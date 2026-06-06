# Changelog

All notable changes to `dynamic-workflows-for-Codex` are documented here.

## v0.6 - 2026-06-06

- Added v3 workflow spec envelopes with procedure graphs.
- Added procedure stages with trigger phrases, gate policy, failure behavior, and final artifacts.
- Added validation for unknown, duplicate, and unstaged work unit references.
- Preserved v2 envelope and v1 plan-root compatibility, including default procedure backfill for legacy v2 specs.
- Bumped package and plugin metadata to `0.6.0`.

## v0.5 - 2026-06-06

- Added `--adapter codex-cli` to run workflow workers through the user's own logged-in `codex exec` CLI without importing OpenAI Agents SDK dependencies.
- Added `cdw doctor` clone-readiness diagnostics for local state, Codex CLI resolution, Codex login status, plugin package presence, and packaged skill presence.
- Added `cdw live-smoke --dry-contract` to print a parseable Codex MCP tool contract without live preflight checks.
- Hardened `cdw live-smoke --execute` so it reuses the validated Codex command and reports live runtime exceptions as check results.
- On Windows, command resolution now skips inaccessible WindowsApps OpenAI.Codex package resources when the user-level Codex CLI exists.
- Bumped package and plugin metadata to `0.5.0`.

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
