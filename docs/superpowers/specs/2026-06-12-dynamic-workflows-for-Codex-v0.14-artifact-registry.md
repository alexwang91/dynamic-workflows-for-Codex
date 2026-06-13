# Dynamic Workflows For Codex v0.14 Artifact Registry Spec

## Goal

Turn v0.13 stage artifact declarations into real persisted run artifacts and
make dependent stages consume those artifacts as execution context.

## Why

v0.13 made workflow specs expressive enough to describe stage dependencies,
consumed artifacts, produced artifacts, and write-policy boundaries. That is a
strong contract, but the runtime still treats artifacts as metadata. v0.14
makes the contract operational: verified stage output becomes files under the
run directory, and later stages receive declared upstream artifacts in their
worker prompts.

## Scope

Artifact persistence:

- Add a run-state artifact index with artifact name, producing stage id, path,
  content type, and source work unit ids.
- Write artifacts under `.cdw/runs/<run-id>/artifacts/<stage-id>/<artifact>.md`.
- Create artifacts only after the producing stage passes its gate.
- Keep writes idempotent so resume can rebuild missing artifacts without
  duplicating index entries.

Stage context hydration:

- Before running a stage, read each declared `consumes` artifact from the run
  artifact index.
- Inject consumed artifact content into the worker prompt for that stage.
- Preserve the original work unit shape for adapters; the runtime passes a
  hydrated copy of the `WorkUnit` to the adapter.
- Do not run a dependent stage before prerequisite gates pass.

CLI inspection:

- `cdw status <run-id>` reports artifact count and artifact paths.
- `cdw status <run-id> --json` includes artifact summaries.
- `cdw artifacts <run-id>` lists persisted artifacts.
- `cdw artifact <run-id> <artifact-name>` prints one artifact's content, with
  `--stage-id` available when names are ambiguous.

Migration behavior:

- The generated migration inventory stage writes a real `migration inventory`
  artifact.
- The guarded migration plan-review stage consumes that artifact after human
  approval.
- The runtime still does not perform write-heavy patches; it only carries
  verified context into guarded planning.

## Non-Goals

- Do not build path-level write enforcement yet.
- Do not introduce a parallel DAG scheduler.
- Do not parse arbitrary worker output into semantic JSON artifacts.
- Do not require old run states to contain artifact indexes.

## Acceptance Criteria

- Passing stages with `produces` write artifact files and persist artifact
  index records in run state.
- Failing stages do not write produced artifacts.
- Dependent stages receive consumed artifact content in their worker prompt.
- Resume is idempotent and does not duplicate artifact records.
- Status and artifacts CLI commands expose artifact metadata and content.
- Migration inventory produces a real artifact before the guarded review stage.
- Existing v1/v2/v3 spec compatibility remains intact.
- Full tests pass.
