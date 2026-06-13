# Dynamic Workflows For Codex v0.15 Path Boundaries Spec

## Goal

Make write-heavy workflow path boundaries executable instead of only documented
in `WorkflowSpecConstraints`.

## Why

v0.13 added `allowed_paths` and `forbidden_paths` to the workflow envelope, and
v0.14 made stage artifacts real. The runtime still does not evaluate whether a
guarded migration plan stays inside its declared filesystem boundary. v0.15
adds a boundary check for declared write paths in guarded/write-heavy stage
outputs.

This does not pretend to sandbox every possible Codex CLI write. It makes the
workflow contract stricter at the planning boundary: if a guarded stage declares
planned write paths, those paths must satisfy the saved workflow constraints.

## Scope

Path declarations:

- Workers can declare planned write paths with sections such as `WRITE_PATHS:`,
  `Planned paths:`, or `Paths:`.
- The boundary checker extracts bullet/list paths from those sections.
- Extracted paths are normalized to forward-slash relative paths.

Boundary checks:

- Forbidden paths always win over allowed paths.
- If `allowed_paths` is non-empty, every declared write path must match at
  least one allowed pattern.
- Absolute paths and parent traversal paths are invalid.
- Read-only stages do not fail only because they mention paths.
- Guarded/write-heavy stages get a `BoundaryResult` recorded in run state.
- A failed boundary result stops the procedure before artifact writing or later
  dependent stages.

CLI:

- `review`, `debug`, `migrate`, `plan`, and `run` accept repeated
  `--allow-path` and `--forbid-path`.
- Direct commands persist constraint overrides into run state.
- Saved specs receive overrides when planning with `--save-spec`.
- `cdw status` and `cdw status --json` show boundary failures.

Migration behavior:

- Generated migration specs forbid common sensitive/runtime paths such as
  `.git/**`, `.cdw/**`, `.agents/**`, and `.env*`.
- Users can add allowed paths at execution/planning time with
  `--allow-path`.

## Non-Goals

- Do not implement a full filesystem sandbox.
- Do not parse arbitrary natural-language path mentions.
- Do not execute patches.
- Do not require fake adapter output to include write paths.
- Do not block read-only inventory stages for listing broad project paths.

## Acceptance Criteria

- Boundary path extraction handles explicit write path sections.
- Boundary checks reject forbidden, outside-allowed, absolute, and parent paths.
- Runtime records boundary results for guarded/write-heavy stages.
- Boundary failures make synthesis incomplete and prevent stage artifacts.
- Passing boundary checks allow guarded stages to complete after human approval.
- CLI constraint overrides affect direct runs and saved specs.
- Status text and JSON include boundary failure summaries.
- Full tests pass.
