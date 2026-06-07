# Dynamic Workflows For Codex v0.10 Dynamic Planner Spec

## Goal

Add an explicit dynamic planning path so `cdw plan` can ask the user's own
Codex CLI to generate a validated v3 workflow spec instead of always using the
static one-worker planning template.

## Why

v0.9 proves the runtime can dispatch real Codex CLI workers, verify them, and
persist structured state. The next gap toward Claude/Superpowers-style dynamic
workflows is planning: the runtime still mostly starts from fixed templates.

v0.10 should make planning itself dynamic while keeping the stable v0.9 path
available.

## Scope

Add a planner mode to `cdw plan`:

```powershell
python -m cdw plan "<request>" --planner codex-cli --save-spec .cdw/specs/task.workflow.json
```

Planner modes:

- `static`: existing behavior and default.
- `fake`: deterministic dynamic spec generator for tests and demos.
- `codex-cli`: shells out to the user's own `codex exec` login state to produce
  a complete v3 `WorkflowSpecBundle`.

The generated spec must validate through the existing Pydantic schemas before
being written. Invalid planner output must fail with a user-facing error and no
traceback.

## Non-Goals

- Do not make `codex-cli` planning the default.
- Do not execute generated workflows during `cdw plan --save-spec`.
- Do not ask for or store API keys.
- Do not loosen existing schema validation.
- Do not replace existing `review`, `debug`, or `migrate` static templates in
  this version.

## Design

Create `cdw.dynamic_planner` with four responsibilities:

- Build a strict planner prompt for Codex CLI.
- Provide a strict JSON output schema to `codex exec --output-schema`.
- Parse JSON from Codex CLI output, including fenced JSON or surrounding CLI
  text.
- Validate the JSON as `WorkflowSpecBundle`.

Add `save_workflow_spec_bundle(path, bundle)` to `cdw.workflow_spec` so dynamic
planning can write a full bundle without rebuilding it from a static
`WorkflowPlan`.

Update `cdw plan` only:

- `--planner static` uses existing `build_plan` and `save_workflow_spec`.
- `--planner fake` writes a deterministic multi-stage dynamic spec.
- `--planner codex-cli` resolves the user's Codex CLI and writes the validated
  model-generated spec.

If `--planner` is used without `--save-spec`, return a clear error. Dynamic
planning produces specs; execution remains a separate `cdw run <spec>` step.

## Acceptance Criteria

- Existing `cdw plan "..." --save-spec <path>` behavior remains unchanged.
- `cdw plan "..." --planner fake --save-spec <path>` writes a valid v3 spec
  with more than one work unit and a procedure graph.
- Dynamic planner parsing accepts raw JSON and fenced JSON output.
- Invalid dynamic planner output fails clearly without traceback.
- `--planner codex-cli` invokes `codex exec -C <root> -s workspace-write
  --output-schema <schema> <prompt>` through the user's resolved Codex CLI.
- Full tests pass.
