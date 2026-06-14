# Consumer Install

This repo is meant to give another Codex user dynamic workflow capability with
their own Codex installation, account, login state, API key, subscription, and
model quota.
It does not ship or require the project author's API key.

## What Gets Installed

- `cdw`: the external dynamic workflow runtime.
- A repo-local Codex plugin marketplace at `.agents/plugins/marketplace.json`.
- A packaged Codex skill at `.agents/plugins/plugins/dynamic-workflows-for-codex/`.

The skill is only an entrypoint. The runtime still owns orchestration, state,
worker dispatch, verification, and synthesis.

## Install From A Clone

```powershell
git clone <repo-url>
cd dynamic-workflows-for-Codex
python -m pip install -e ".[dev]"
python -m cdw bootstrap
python -m cdw doctor
```

`bootstrap` refreshes the repo-local marketplace and plugin package, then prints
the next commands for marketplace registration and verification.

`doctor` checks local state writeability, the repo-local plugin package, the
packaged skill, and the user's own Codex CLI. It does not run a real worker,
consume model quota, or require the project author's API key.

If `doctor` reports that the discovered `codex` command is missing or not
directly executable, point `cdw` at the user's own Codex CLI:

```powershell
$env:CDW_CODEX_COMMAND = "C:\path\to\codex.exe"
python -m cdw doctor
```

For fake-mode development and tests, live dependencies and keys are not needed:

```powershell
python -m pip install -e ".[dev]"
python -m pytest
python -m cdw review "Review this branch" --adapter fake
```

For the closest clone-and-use path, use the user's logged-in Codex CLI:

```powershell
codex login status
python -m cdw review "Review this branch" --adapter codex-cli
```

`--adapter codex-cli` shells out to the user's own `codex exec`. It does not
need this repo to know or store the user's API key.

## Add The Plugin Marketplace To Codex

The repo includes a marketplace file and plugin package:

```text
.agents/plugins/marketplace.json
.agents/plugins/plugins/dynamic-workflows-for-codex/
```

When Codex needs an explicit marketplace registration, add the marketplace root:

```powershell
python -m cdw bootstrap
codex plugin marketplace add .agents/plugins
```

Then install or enable `dynamic-workflows-for-codex` from that marketplace in
the user's Codex environment.

## Use It

From the cloned repo:

```powershell
python -m cdw plan "Review this branch" --planner codex-cli --save-spec .cdw/specs/review.workflow.json
python -m cdw run .cdw/specs/review.workflow.json --adapter codex-cli
python -m cdw status <run-id>
python -m cdw artifacts <run-id>
python -m cdw artifact <run-id> "synthesis report"
python -m cdw runs
python -m cdw migrate "Rename User model to Account" --adapter codex-cli
python -m cdw migrate "Rename User model to Account" --allow-path "src/**" --forbid-path ".env*" --adapter codex-cli
```

Use `--planner codex-cli` when the user's own Codex CLI should design a
task-specific workflow spec from a broad request. Use `--planner fake` for
deterministic demos and tests. The default `--planner static` preserves the
older fixed planning template.

Saved workflow specs can express stage dependencies, consumed and produced
artifacts, and per-stage write-policy boundaries. The runtime will not run a
dependent stage until its prerequisite stages pass their gates, and write-heavy
workflow specs require human approval boundaries.

When a stage passes and declares `produces`, the runtime writes markdown
artifacts under `.cdw/runs/<run-id>/artifacts/`. A later stage that declares
`consumes` receives those verified artifacts in its worker prompt. Use
`cdw artifacts <run-id>` to list them and `cdw artifact <run-id> "<artifact name>"`
to inspect one.

For guarded/write-heavy work, add repeated `--allow-path <glob>` and
`--forbid-path <glob>` flags when planning or running specs. Guarded stages can
declare `WRITE_PATHS:` in their output; the runtime records boundary failures
when a declared path is forbidden, outside the allowlist, absolute, or uses
parent traversal.

Generated migration workflows are stricter: they set
`requires_write_contract=true` and require a structured `WRITE_CONTRACT` JSON
section before the guarded plan-review stage can write artifacts or feed a
future write phase:

```text
WRITE_CONTRACT:
{
  "paths": [
    {"path": "src/users.py", "action": "modify", "reason": "Rename User"}
  ],
  "checks": ["python -m pytest tests/test_users.py"]
}
```

`cdw status <run-id> --json` exposes `contract_required`, `contract_found`,
parsed `declared_write_paths`, planned `contract_checks`, and any boundary
violations.

When a structured contract passes, `cdw` also writes a `write phase draft`
artifact. It is a reviewable markdown draft containing planned paths, actions,
reasons, and checks. It is intentionally non-executing: it does not apply
patches or modify source files.

```powershell
python -m cdw artifacts <run-id>
python -m cdw artifact <run-id> "write phase draft"
```

Use `cdw status <run-id>` before resuming a workflow. It reports the synthesis
status, pending human approval stage, state path, and adapter-aware approval
resume command. Use `cdw status <run-id> --json` or `cdw runs --json` when a
Codex skill needs machine-readable status.

Some guarded workflows pause with `waiting_for_human`. Review the pending stage
from `cdw status <run-id>`, then resume only after approval:

```powershell
python -m cdw resume <run-id> --adapter codex-cli --approve-human-gates
```

That approval applies only to the current pending stage. If a later stage also
requires human approval, the run pauses again.

Use fake mode for deterministic tests and demos:

```powershell
python -m cdw run .cdw/specs/review.workflow.json --adapter fake
python -m cdw migrate "Rename User model to Account" --adapter fake
```

## Optional Live Adapter

The default real clone-and-use path is `--adapter codex-cli`. Live mode is an
optional OpenAI Agents SDK path for testing the Codex MCP boundary:

```powershell
python -m pip install -e ".[live]"
python -m cdw live-smoke --dry-contract
python -m cdw live-smoke
$env:OPENAI_API_KEY = "<your-openai-api-key>"
python -m cdw live-smoke --execute
python -m cdw review "Review this branch" --adapter live
```

`live-smoke --dry-contract` prints the Codex MCP tool contract that would be
used for the live smoke worker. It does not require `OPENAI_API_KEY`, the
OpenAI Agents SDK, or a working `codex` command.

Do not commit secrets. `.cdw/` is ignored and stores local run state and
workflow artifacts only.
