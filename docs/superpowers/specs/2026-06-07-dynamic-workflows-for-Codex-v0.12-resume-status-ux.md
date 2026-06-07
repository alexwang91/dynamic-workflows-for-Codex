# Dynamic Workflows For Codex v0.12 Resume Status UX Spec

## Goal

Make persisted workflow runs easy for Codex and humans to inspect before
resuming, especially when v0.11 human approval gates pause execution.

## Why

v0.11 can pause a workflow at a human-gated stage, but the user or installed
skill still has to know where to look in `.cdw/runs/<run-id>/state.json`.
That is workable for developers, but too low-level for a clone-and-use
workflow. v0.12 should expose a small, stable CLI surface for answering:

- Which runs exist?
- What is this run's status?
- Which stage is waiting for human approval?
- What exact resume command should be run after approval?

## Scope

Add two read-only CLI commands:

- `cdw status <run-id> --root <repo>` prints one run summary.
- `cdw runs --root <repo>` prints recent run summaries.

Both commands support `--json` for skill/plugin automation.

## Output Contract

`cdw status <run-id>` human output includes:

- `run <run-id>`
- `status <complete|incomplete|waiting_for_human|unknown>`
- `command <plan.command>`
- `request <plan.request>`
- `adapter <adapter>` when the run was started through the CLI.
- `pending <stage-id>` only when `pending_human_approval` is set.
- `resume python -m cdw resume <run-id> --adapter <adapter> --approve-human-gates`
  only when waiting for human approval and the adapter is known.
- `state <path-to-state.json>`

`cdw status <run-id> --json` outputs an object with:

```json
{
  "run_id": "abc123",
  "status": "waiting_for_human",
  "command": "migrate",
  "request": "Rename User model to Account",
  "adapter": "codex-cli",
  "pending_human_approval": "migration-plan-review",
  "worker_count": 1,
  "verification_count": 1,
  "state_path": ".cdw/runs/abc123/state.json",
  "resume_command": "python -m cdw resume abc123 --adapter codex-cli --approve-human-gates"
}
```

`cdw runs` human output prints one line per run:

```text
run abc123 status waiting_for_human command migrate adapter codex-cli pending migration-plan-review
```

`cdw runs --json` outputs a list of the same summary objects. Runs are sorted
newest first by `state.json` modification time.

## Error Handling

- Missing run state prints `error: run not found: <run-id>` and exits non-zero.
- Missing `.cdw/runs` is not an error for `cdw runs`; it prints no human lines
  or `[]` for JSON.
- Corrupt run states are skipped by `cdw runs` so one bad file does not hide all
  other runs.
- `cdw status` on a corrupt run surfaces the validation or parse error as a
  user-facing `error: ...` line.

## Non-Goals

- Do not add interactive approval prompts.
- Do not add a database or index file. Persist only the adapter name needed for
  accurate resume hints.
- Do not execute workers from `status` or `runs`.
- Do not merge status inspection with `doctor`; this is run-state UX, not clone
  readiness.

## Acceptance Criteria

- `cdw status <run-id>` reports a paused human-gated run and prints the pending
  stage.
- `cdw status <run-id> --json` returns a parseable summary object.
- `cdw runs` lists existing runs newest first.
- `cdw runs --json` returns parseable summaries.
- Missing run ids fail with a user-facing error and no traceback.
- Full tests pass.
