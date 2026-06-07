---
name: dynamic-workflows-for-codex
description: Use when a Codex task needs dynamic workflow orchestration for branch review, debugging, resumable workflow specs, guarded migrations, staged procedure execution, or clone-user readiness checks.
---

# Dynamic Workflows For Codex

Use the `cdw` runtime. The runtime owns orchestration, state, worker dispatch, verification, and synthesis.

## Trigger Routing

Use this skill when the user asks for any of these:

- Branch or PR review with multiple specialist perspectives.
- Debugging that needs parallel hypotheses or repeatable investigation.
- Guarded migrations, write-heavy refactors, or ownership-bounded changes.
- Reusable workflow specs, staged procedure graphs, or resumable runs.
- Dynamic workflow planning from a broad request.
- Clone/install readiness checks for this plugin or runtime.

Route first-time clone setup to `cdw bootstrap --root <repo>` and then
`cdw doctor --root <repo>`.
Route broken-environment reports to `cdw doctor --root <repo>`.
Route existing run ids to `cdw resume <run-id>` before starting new work.
Route reusable multi-step work through `cdw plan --planner codex-cli
--save-spec` followed by `cdw run <workflow-spec>`.
If a run reports `waiting_for_human`, report the pending stage and wait for
the user to approve before running `cdw resume <run-id> --approve-human-gates`.

## Operating Loop

Run `cdw bootstrap --root <repo>` after cloning or packaging changes. It
refreshes the repo-local plugin marketplace and packaged skill, then prints the
marketplace registration and doctor commands.

Run `cdw doctor --root <repo>` before real workflows. It verifies local state
writeability, the repo-local plugin package, the packaged skill, and the user's
own Codex CLI without running a real worker or requiring the project author's
API key.

If `codex` is not on PATH, rerun doctor with `--codex-command <path>` or set
`CDW_CODEX_COMMAND`.

For multi-step work, prefer a saved workflow spec:

1. Run `cdw plan "<request>" --planner codex-cli --save-spec .cdw/specs/<name>.workflow.json`.
2. Run `cdw run .cdw/specs/<name>.workflow.json --adapter codex-cli`.
3. Report the run id and state path under `.cdw/runs/<run-id>/state.json`.
4. If interrupted, partially complete, or waiting for human approval, resume the same run id.

For direct task-specific workflows, use `review`, `debug`, or `migrate` with
the same adapter policy below.

## Adapter Policy

- Use `--adapter codex-cli` for real clone-and-use workflows. It shells out to
  the user's own `codex exec` login state.
- Use `--adapter fake` for deterministic tests, demos, and documentation
  examples.
- Use `--adapter live` only when explicitly testing the optional OpenAI Agents
  SDK / Codex MCP path.

## Planner Policy

- Use `--planner codex-cli` when the user wants Codex to design a task-specific
  workflow spec from a broad request.
- Use `--planner static` when preserving the old fixed planning template.
- Use `--planner fake` for deterministic tests and demos.
- Dynamic planner modes require `--save-spec`; planning writes a validated spec
  and does not execute workers.

## Approval Policy

- Treat `waiting_for_human` as a real stop, not a failure to work around.
- Report the pending stage from `.cdw/runs/<run-id>/state.json`.
- Ask the user before passing `--approve-human-gates`.
- After approval, run `cdw resume <run-id> --adapter codex-cli --approve-human-gates`.

## Resume First

If the user gives a run id, mentions an interrupted workflow, or asks to
continue previous dynamic workflow work, run:

```bash
cdw resume <run-id> --adapter codex-cli
```

Do this before creating a new spec or starting new workers. The runtime persists
worker results, verifier results, synthesis, and staged procedure state.

## Command Map

- Run `cdw plan "<request>" --planner codex-cli --save-spec <file>` to create a dynamic reusable workflow spec.
- Run `cdw plan "<request>" --save-spec <file>` to create a static reusable workflow spec.
- Run `cdw bootstrap --root <repo>` to refresh repo-local plugin packaging and print install next steps.
- Run `cdw review "<request>" --adapter codex-cli` for a real review workflow through the user's logged-in Codex CLI.
- Run `cdw debug "<request>" --adapter codex-cli` for hypothesis-driven debugging.
- Run `cdw run <workflow-spec> --adapter codex-cli` to execute a saved workflow with Codex CLI workers.
- Run `cdw resume <run-id> --adapter codex-cli` to continue a partial run.
- Run `cdw resume <run-id> --adapter codex-cli --approve-human-gates` only after the user approves a pending human gate.
- Run `cdw migrate "<request>" --adapter codex-cli` for guarded migration planning.
- Run `cdw package-plugin --repo-marketplace --root <repo>` after packaging changes.
- Use `--adapter fake` for deterministic tests and demos.

## Guardrails

- Do not ask for or assume the project author's API key.
- Do not replace the runtime with free-form prompt orchestration.
- Do not run real workers until `cdw doctor` passes or the user explicitly
  accepts the local readiness failure.
- Do not pass `--approve-human-gates` unless the user explicitly approves the
  pending stage.
- Do not use `live-smoke --execute` unless the user explicitly wants the
  optional Agents SDK live path.
- Keep `.cdw/` local. It stores workflow specs and run state, not secrets.
