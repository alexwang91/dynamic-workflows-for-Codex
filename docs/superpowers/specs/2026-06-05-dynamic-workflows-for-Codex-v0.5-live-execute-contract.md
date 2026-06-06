# dynamic-workflows-for-Codex v0.5 Live Execute Contract Design

## Goal

Make `cdw live-smoke --execute` a trustworthy diagnostic for the live adapter path.

## Context

v0.4 made the Codex CLI command configurable through `--codex-command` and
`CDW_CODEX_COMMAND`. That fixed preflight command selection, but the execute
path still needs a tighter contract:

- The smoke check can validate one command while the live adapter launches the
  default `codex` command.
- A live execution failure can escape as a traceback instead of a structured
  smoke report.

This is the next smallest useful step toward a real Claude-style dynamic
workflow: before expanding workflow specs or plugin packaging, the live path
must be honest about what it is about to run and what failed.

## Requirements

- `run_live_smoke(..., execute=True, codex_command=...)` must pass the resolved
  command into `LiveCodexAdapter`.
- `run_live_smoke(..., execute=True)` must report live execution exceptions as a
  failed `live-run` check instead of crashing.
- A successful execute smoke should add an `ok` `live-run` check and preserve the
  returned run id.
- `LiveCodexAdapter` must build the Codex MCP tool request through a parseable
  contract object instead of relying only on free-form prose.
- The generated instruction must still tell the coordinating agent to call the
  Codex MCP `codex` tool exactly once with `prompt`, `cwd`, `sandbox`, and
  `approval-policy`.
- `cdw live-smoke --dry-contract` must print the live-smoke Codex MCP tool
  contract as JSON without checking imports, API keys, or a Codex CLI binary.
- `--adapter codex-cli` must execute workers through the user's own logged-in
  `codex exec` command without requiring `OPENAI_API_KEY` or the OpenAI Agents
  SDK.
- The Codex CLI adapter must use the same command resolver as live mode, so a
  cloned repo can find the user's local Codex CLI automatically when possible.
- Unit tests must not require `openai`, `openai-agents`, an API key, or a real
  Codex CLI.

## Non-Goals

- Do not change the workflow spec language.
- Do not add resume semantics in this step.
- Do not change plugin packaging in this step.
- Do not require a successful live OpenAI/Codex call on this machine.
- Do not change authentication behavior or ask users to share API keys.

## Acceptance Checks

- `python -m pytest tests/test_live_smoke.py -v` proves the execute path uses the
  resolved Codex command and reports live-run failures.
- `python -m pytest tests/test_codex_mcp.py -v` proves the MCP tool contract is
  parseable and includes the exact execution arguments.
- `python -m cdw live-smoke --dry-contract` prints JSON and exits zero even on a
  machine without live dependencies.
- `python -m pytest tests/test_codex_cli.py -v` proves the Codex CLI adapter
  calls `codex exec` with root, sandbox, approval policy, and scoped prompts.
- `python -m cdw plan "Review branch" --adapter codex-cli` can run without
  importing OpenAI Agents SDK dependencies when `codex exec` is mocked in tests.
- `python -m pytest -v` passes.
- `python -m cdw live-smoke` still reports local environment blockers cleanly.
