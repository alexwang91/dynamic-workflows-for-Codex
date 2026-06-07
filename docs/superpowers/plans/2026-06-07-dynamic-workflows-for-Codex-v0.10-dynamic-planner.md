# Dynamic Workflows For Codex v0.10 Dynamic Planner Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add explicit dynamic planner modes for `cdw plan` so clone users can generate validated v3 workflow specs with their own Codex CLI.

**Architecture:** Keep the existing static planner as the default. Add a focused `cdw.dynamic_planner` module that generates or parses `WorkflowSpecBundle` objects, and add a bundle writer in `cdw.workflow_spec`. The CLI wires dynamic planner modes only when `cdw plan --save-spec` is used.

**Tech Stack:** Python 3.10+, argparse, pydantic, pytest, local Codex CLI.

---

## File Structure

- Create `src/cdw/dynamic_planner.py`: fake planner, Codex CLI planner, JSON extraction, schema validation.
- Modify `src/cdw/workflow_spec.py`: add `save_workflow_spec_bundle`.
- Modify `src/cdw/cli.py`: add `--planner {static,fake,codex-cli}` for `plan`.
- Create `tests/test_dynamic_planner.py`: unit tests for fake planner, JSON parsing, invalid output, and Codex CLI args.
- Modify `tests/test_cli.py`: CLI tests for dynamic planner routing and error handling.
- Modify release docs and metadata for v0.10.

## Task 1: Dynamic Planner Unit Tests

- [ ] **Step 1: Write fake planner test**

Assert `build_dynamic_workflow_spec("Review auth migration", "fake", root)` returns a v3 bundle with at least two work units and a valid procedure.

- [ ] **Step 2: Write parser tests**

Assert `parse_dynamic_planner_output` accepts raw JSON and fenced JSON, and raises `RuntimeError` with `dynamic planner returned invalid workflow spec` for invalid output.

- [ ] **Step 3: Write Codex CLI args test**

Monkeypatch `subprocess.run`, call the Codex planner, and assert args use
`codex-test exec -C <root> -s workspace-write --output-schema <schema>
<prompt>` with no `-a`.

- [ ] **Step 4: Verify red**

Run:

```powershell
python -m pytest tests/test_dynamic_planner.py -v
```

Expected: import failures because `cdw.dynamic_planner` does not exist.

## Task 2: Dynamic Planner Implementation

- [ ] **Step 1: Add fake planner**

Create deterministic `WorkflowSpecBundle` output with staged inventory and plan-review work units.

- [ ] **Step 2: Add JSON extraction**

Support raw JSON and ```json fenced output. Reject missing or malformed JSON.

- [ ] **Step 3: Add Codex CLI planner**

Shell out to `codex exec`, clean Windows process-cleanup noise, parse output,
provide a strict output schema, and validate `WorkflowSpecBundle`.

- [ ] **Step 4: Verify focused green**

Run:

```powershell
python -m pytest tests/test_dynamic_planner.py -v
```

Expected: all dynamic planner tests pass.

## Task 3: CLI Wiring

- [ ] **Step 1: Add `save_workflow_spec_bundle`**

Write an already-built bundle to disk without rebuilding static defaults.

- [ ] **Step 2: Add `--planner` to `plan` command**

Default is `static`. Dynamic planners require `--save-spec`; without it, return
1 with a clear stderr message.

- [ ] **Step 3: Add CLI tests**

Assert `--planner fake --save-spec` writes a dynamic multi-work-unit spec.
Assert `--planner fake` without `--save-spec` fails clearly.

- [ ] **Step 4: Verify focused green**

Run:

```powershell
python -m pytest tests/test_cli.py tests/test_workflow_spec.py tests/test_dynamic_planner.py -v
```

Expected: focused tests pass.

## Task 4: Release Surface

- [ ] **Step 1: Bump metadata to `0.10.0`**

Update `pyproject.toml`, plugin manifest generation, repo-local plugin manifest,
and plugin package tests.

- [ ] **Step 2: Update README, CHANGELOG, evaluation, consumer install, and skill routing**

Document dynamic planner modes and keep static mode as default.

- [ ] **Step 3: Verify docs mention user-owned Codex auth**

Ensure docs do not imply project-owned API keys or hidden service credentials.

## Task 5: Verification And Commit

- [ ] **Step 1: Run full tests**

```powershell
python -m pytest -v
```

- [ ] **Step 2: Run readiness checks**

```powershell
python -m cdw doctor
python -m cdw live-smoke
python -m cdw bootstrap
python C:\Users\Administrator\.codex\skills\.system\plugin-creator\scripts\validate_plugin.py .agents\plugins\plugins\dynamic-workflows-for-codex
```

- [ ] **Step 3: Optional real planner smoke**

If quota is available, run:

```powershell
python -m cdw plan "Create a dynamic review workflow for this branch" --planner codex-cli --save-spec .cdw/specs/v0.10-smoke.workflow.json
```

Expected: spec writes and validates. Do not run the generated workflow unless explicitly requested.

- [ ] **Step 4: Commit and push**

```powershell
git add .
git commit -m "feat: add dynamic workflow planner"
git push -u origin codex/dynamic-planner-v0.10
```
