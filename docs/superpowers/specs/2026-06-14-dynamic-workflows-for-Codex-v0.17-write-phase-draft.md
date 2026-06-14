# Dynamic Workflows For Codex v0.17 Write Phase Draft Spec

## Goal

Turn validated `WRITE_CONTRACT` data into a durable, reviewable write-phase
draft artifact without modifying project source files.

## Why

v0.16 gives guarded/write-heavy stages a machine-readable write contract. The
next safe step is not automatic patch execution. It is an auditable bridge:
render the parsed contract into a stable artifact that a human or future
executor can review before any write-heavy phase runs.

## Scope

- Add a small write-draft module that renders a markdown artifact from a passed
  `BoundaryResult`.
- Generate the draft only when:
  - the stage is guarded/write-heavy,
  - the boundary result passed,
  - the boundary result found structured write paths.
- Persist the draft under the existing run artifact registry as
  `write phase draft`.
- Include stage id, contract status, each planned path, action, reason, planned
  checks, and explicit next-step guidance.
- Keep artifact generation idempotent across resume.
- Do not execute patches or modify contract paths.

## Non-Goals

- Do not apply patches.
- Do not synthesize diffs.
- Do not shell out to Codex for write execution.
- Do not require read-only workflows to produce write drafts.

## Acceptance Criteria

- A passed strict guarded stage with structured contract paths writes a
  `write phase draft` artifact.
- A failed boundary result does not write the draft.
- A legacy `WRITE_PATHS`-only result does not write the draft.
- Resume does not duplicate draft artifact records.
- `cdw artifacts` and `cdw artifact` can list and read the draft through the
  existing artifact commands.
- Docs, skill, plugin metadata, package version, and test badge are updated to
  `0.17.0`.
- Full tests pass.
