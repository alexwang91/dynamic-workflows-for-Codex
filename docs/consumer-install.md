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
python -m cdw migrate "Rename User model to Account" --adapter codex-cli
```

Use `--planner codex-cli` when the user's own Codex CLI should design a
task-specific workflow spec from a broad request. Use `--planner fake` for
deterministic demos and tests. The default `--planner static` preserves the
older fixed planning template.

Some guarded workflows pause with `waiting_for_human`. Review the pending stage
in `.cdw/runs/<run-id>/state.json`, then resume only after approval:

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

Do not commit secrets. `.cdw/` is ignored and stores local run state only.
