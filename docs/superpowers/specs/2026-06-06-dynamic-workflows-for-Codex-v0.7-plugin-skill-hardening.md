# Dynamic Workflows For Codex v0.7 Plugin Skill Hardening Spec

## Goal

Make the packaged Codex skill behave more like a Superpowers/Matt-style
workflow skill: clear trigger conditions, a repeatable operating loop, command
routing, authentication boundaries, and resume-first behavior.

## Why

The current packaged skill explains that `cdw` owns orchestration and lists
commands, but it is still mostly a command reference. A clone user needs Codex
to know when to use the runtime, which adapter to choose, when to run `doctor`,
and how to avoid drifting back into free-form prompt orchestration.

## Scope

Update generated and repo-local skill content so it includes:

- Trigger routing for review, debug, migration, saved workflow specs, and resume.
- A first-run readiness loop based on `cdw doctor`.
- Adapter policy: prefer `codex-cli` for real workflows, `fake` for tests, `live`
  only when explicitly testing the optional Agents SDK path.
- Resume-first behavior when an existing run id is present.
- Workflow spec behavior: create reusable specs for multi-step work, then run
  specs instead of rebuilding plans.
- Guardrails: do not ask for the project author's API key, do not replace
  runtime orchestration with ad hoc subagents, and do not run real workers
  without the user's own Codex CLI/authentication.

Also update plugin metadata so marketplace descriptions mention clone-user
readiness and Codex CLI dynamic workflows.

## Non-Goals

- Do not change runtime execution.
- Do not add new commands.
- Do not create a separate plugin scaffold.
- Do not run a real Codex worker smoke test.

## Acceptance Criteria

- `build_skill_content()` includes trigger routing, operating loop, adapter
  policy, resume-first behavior, and guardrails.
- The repo-local packaged `SKILL.md` matches the generated skill content.
- Plugin metadata version is `0.7.0`.
- Plugin metadata mentions `doctor`, `codex-cli`, and workflow specs.
- Plugin validation succeeds.
- Full test suite passes.
