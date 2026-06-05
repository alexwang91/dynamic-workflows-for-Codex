# Evaluation Checklist

## Architecture

- Runtime state is stored in `.cdw/runs/<run-id>/state.json`.
- Worker results are structured and persisted before verification.
- Verification results are persisted before synthesis.
- Synthesis reads structured state, not chat transcript history.

## MVP Behavior

- `cdw plan` creates a durable run directory.
- `cdw review` fans out to security, tests, compatibility, and maintainability workers.
- `cdw debug` fans out to logs, tests, code-path, and timing investigators.
- Fake adapter mode works without OpenAI credentials.
- Live adapter mode fails clearly when optional dependencies are missing.
- Live adapter mode constructs a `codex mcp-server` stdio server through the Agents SDK.

## v0.2 Behavior

- `cdw plan --save-spec` writes a reusable workflow spec without executing it.
- `cdw run <workflow-spec>` validates and executes a saved workflow spec.
- `cdw resume <run-id>` reuses persisted worker and verifier results instead of starting over.
- `cdw migrate` creates a guarded migration workflow with ownership boundaries and patch-review gates.
- `cdw install-skill` writes a repo-local skill that delegates orchestration to `cdw`.

## v0.3 Behavior

- `cdw live-smoke` reports live-mode prerequisites without traceback or secret leakage.
- `cdw live-smoke --execute` performs an actual minimal live worker run only after prerequisites pass.
- Saved workflow specs use a v2 envelope with metadata, constraints, acceptance criteria, and embedded plan.
- v1 plan-root workflow specs remain loadable for backward compatibility.
- `cdw package-plugin` writes a local Codex plugin package with `.codex-plugin/plugin.json` and a packaged skill.
- The plugin package validates with the plugin-creator validator.
