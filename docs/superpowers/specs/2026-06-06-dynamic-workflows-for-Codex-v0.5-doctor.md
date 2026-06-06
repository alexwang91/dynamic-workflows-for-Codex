# Dynamic Workflows For Codex v0.5 Doctor Spec

## Goal

Add `cdw doctor` as the first clone-user diagnostic command. It verifies that the
repo, plugin package, and user's own Codex CLI are ready for dynamic workflows
without running a real worker, consuming model quota, or requiring the project
author's API key.

## User Story

A user clones `dynamic-workflows-for-Codex`, installs the package, and runs:

```powershell
python -m cdw doctor
```

The command reports clear `ok` / `failed` checks and gives enough detail to fix
missing Codex CLI, login, package, or write-permission problems.

## Scope

`cdw doctor` checks:

- Local runtime importability.
- Root writeability for `.cdw` run state.
- Codex command resolution through `--codex-command`, `CDW_CODEX_COMMAND`, or PATH.
- `codex --version`.
- `codex login status`.
- `codex exec --help`.
- Repo-local plugin marketplace package presence.
- Packaged skill presence.

## Non-Goals

- It does not call `codex exec` with a real prompt.
- It does not check `OPENAI_API_KEY`.
- It does not validate OpenAI Agents SDK live-mode execution.
- It does not install Codex, log the user in, or change plugin state.

## Output Contract

Text output follows the same shape as `live-smoke`:

```text
cdw-runtime: ok - cdw runtime importable
cdw-state: ok - .cdw state directory writable
codex-command: ok - source=path command=C:\path\to\codex.exe
codex-version: ok - codex-cli 0.130.0-alpha.5
codex-login: ok - logged in
codex-exec: ok - codex exec help available
plugin-package: ok - repo-local plugin package present
skill-package: ok - packaged skill present
```

Exit code is `0` when all checks pass and `1` when any check fails.

## Design

Create a focused `cdw.doctor` module with a `DoctorReport` and reusable
`CheckResult` style. The module uses the existing `resolve_codex_command`
function so WindowsApps fallback behavior and explicit command overrides stay
consistent across `doctor`, `live-smoke`, and workflow execution.

The CLI adds:

```powershell
python -m cdw doctor --root . --codex-command C:\path\to\codex.exe
```

Tests monkeypatch `subprocess.run` and command resolution inputs so no real
Codex installation is required.

## Acceptance Criteria

- `cdw doctor` exists in the CLI parser.
- `cdw doctor` never asks for or checks the project author's API key.
- Missing Codex CLI is reported as a failed check without traceback.
- Successful mocked diagnostics return a report whose `.ok` is true.
- Plugin and packaged skill checks point at the repo-local package layout.
- README, consumer docs, evaluation docs, and packaged skill copy describe
  `cdw doctor` as the first troubleshooting command.
