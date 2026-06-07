# Changelog

All notable changes to `dynamic-workflows-for-Codex` are documented here.

## v0.11 - 2026-06-07

- Added runtime pauses before `manual_review` and `require_human` stages.
- Added `pending_human_approval` to persisted run state.
- Added `waiting_for_human` synthesis status and user-facing CLI output.
- Added `--approve-human-gates` to `resume` for approving the currently pending human-gated stage.
- Later human-gated stages pause again instead of inheriting a previous approval.
- Guarded migration workflows now stop after read-only inventory before the manual migration-plan review stage.
- Bumped package and plugin metadata to `0.11.0`.

## v0.10 - 2026-06-07

- Added `cdw plan --planner {static,fake,codex-cli}`.
- Added a deterministic fake dynamic planner that writes validated multi-stage v3 workflow specs.
- Added a Codex CLI dynamic planner that asks the user's own `codex exec` to generate a full `WorkflowSpecBundle`.
- Added JSON and fenced-JSON extraction plus schema validation for dynamic planner output.
- Added strict `--output-schema` guidance for Codex CLI planner output before final Pydantic validation.
- Added user-facing CLI errors when dynamic planner output is malformed or `--planner` is used without `--save-spec`.
- Bumped package and plugin metadata to `0.10.0`.

## v0.9 - 2026-06-06

- Fixed `--adapter codex-cli` to use the current `codex exec -C <root> -s <sandbox> <prompt>` argument shape.
- Removed the unsupported approval-policy CLI argument from Codex CLI worker execution.
- Added a regression assertion so the adapter cannot reintroduce the old `-a` flag.
- Filtered Windows Codex CLI process-cleanup noise before persisting worker output or parsing verifier verdicts.
- Hardened CLI run commands to return non-zero when verification leaves a workflow incomplete.
- Captured real codex-cli smoke failures as regression coverage; final live pass still depends on the clone user's available Codex quota.
- Bumped package and plugin metadata to `0.9.0`.

## v0.8 - 2026-06-06

- Added `cdw bootstrap` to refresh the repo-local plugin marketplace and package.
- Bootstrap output now prints the next marketplace registration and doctor commands for clone users.
- Updated clone install docs to run bootstrap before doctor.
- Bumped package and plugin metadata to `0.8.0`.

## v0.7 - 2026-06-06

- Hardened the packaged Codex skill with trigger routing, an operating loop, adapter policy, resume-first behavior, command map, and guardrails.
- Updated repo-local plugin metadata to mention `cdw doctor`, `codex-cli`, and reusable workflow specs.
- Added tests to keep generated skill content and repo-local packaged skill content in sync.
- Bumped package and plugin metadata to `0.7.0`.

## v0.6 - 2026-06-06

- Added v3 workflow spec envelopes with procedure graphs.
- Added procedure stages with trigger phrases, gate policy, failure behavior, and final artifacts.
- Added staged runtime execution for `cdw run <workflow-spec>`.
- Persisted procedure graphs in run state so `resume` preserves staged behavior.
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
