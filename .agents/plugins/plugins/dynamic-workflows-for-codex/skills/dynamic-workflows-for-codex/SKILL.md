---
name: dynamic-workflows-for-codex
description: Use when a Codex task needs an external dynamic workflow runtime, including multi-agent review, debugging, resumable workflow specs, or guarded migrations.
---

# Dynamic Workflows For Codex

Use the `cdw` runtime. The runtime owns orchestration, state, worker dispatch, verification, and synthesis.

## Commands

- Run `cdw plan "<request>" --save-spec <file>` to create a reusable workflow spec.
- Run `cdw run <workflow-spec>` to execute a saved workflow.
- Run `cdw resume <run-id>` to continue a partial run.
- Run `cdw migrate "<request>"` for guarded migration planning.

Do not replace the runtime with free-form prompt orchestration.
