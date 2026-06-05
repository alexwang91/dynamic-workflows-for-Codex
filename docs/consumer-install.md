# Consumer Install

This repo is meant to give another Codex user dynamic workflow capability with
their own Codex installation, account, API key, subscription, and model quota.
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
python -m pip install -e ".[live]"
python -m cdw live-smoke --dry-contract
python -m cdw live-smoke
```

`live-smoke --dry-contract` prints the Codex MCP tool contract that would be
used for the live smoke worker. It does not require `OPENAI_API_KEY`, the
OpenAI Agents SDK, or a working `codex` command.

If `live-smoke` reports that the discovered `codex` command is not directly
executable, point `cdw` at the user's own Codex CLI:

```powershell
$env:CDW_CODEX_COMMAND = "C:\path\to\codex.exe"
python -m cdw live-smoke
```

For fake-mode development and tests, live dependencies and keys are not needed:

```powershell
python -m pip install -e ".[dev]"
python -m pytest
python -m cdw review "Review this branch" --adapter fake
```

## Add The Plugin Marketplace To Codex

The repo includes a marketplace file and plugin package:

```text
.agents/plugins/marketplace.json
.agents/plugins/plugins/dynamic-workflows-for-codex/
```

When Codex needs an explicit marketplace registration, add the marketplace root:

```powershell
codex plugin marketplace add .agents/plugins
```

Then install or enable `dynamic-workflows-for-codex` from that marketplace in
the user's Codex environment.

## Use It

From the cloned repo:

```powershell
python -m cdw plan "Review this branch" --save-spec .cdw/specs/review.workflow.json
python -m cdw run .cdw/specs/review.workflow.json --adapter fake
python -m cdw migrate "Rename User model to Account" --adapter fake
```

For live mode, the user must provide their own OpenAI/Codex authentication:

```powershell
$env:OPENAI_API_KEY = "<your-openai-api-key>"
python -m cdw live-smoke --execute
python -m cdw review "Review this branch" --adapter live
```

Do not commit secrets. `.cdw/` is ignored and stores local run state only.
