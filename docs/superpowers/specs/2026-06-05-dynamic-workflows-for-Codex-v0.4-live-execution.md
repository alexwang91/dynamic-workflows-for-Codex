# dynamic-workflows-for-Codex v0.4 Live Execution Design

## Goal

Make live execution configurable enough to diagnose and work around local Codex CLI launch problems, especially Windows `Access denied` failures from the WindowsApps command shim.

## Context

v0.3 added `cdw live-smoke`. On this machine it reports:

- `agents` is not installed.
- `openai` is not installed.
- `codex` is discoverable under `C:\Program Files\WindowsApps\...`.
- Running `codex --version` fails with Windows access denied.

The next useful step is to make Codex command resolution explicit and reusable across both smoke checks and live adapter execution.

## Requirements

- Add configurable Codex command resolution:
  - CLI flag: `--codex-command <path-or-command>` for live-capable commands.
  - Environment variable: `CDW_CODEX_COMMAND`.
  - Default fallback: `codex` from PATH.
- `cdw live-smoke` should report which source selected the Codex command.
- `LiveCodexAdapter` should use the resolved command when launching `codex mcp-server`.
- CLI live commands should pass the resolved command into `LiveCodexAdapter`.
- Diagnostics should include an actionable hint when a WindowsApps path fails with access denied.
- Unit tests must not require live dependencies or a working Codex CLI.

## Non-Goals

- Do not install `openai` or `openai-agents`.
- Do not change OpenAI API authentication behavior.
- Do not publish or install plugins globally.
- Do not require live execution in CI.

## Acceptance Checks

- `python -m pytest -v` passes.
- `python -m cdw live-smoke` still reports current local blockers cleanly.
- `python -m cdw live-smoke --codex-command <fake-command>` honors explicit command selection in tests.
- `LiveCodexAdapter` uses a configured command in MCP server params.
