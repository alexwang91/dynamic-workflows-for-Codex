# Dynamic Workflows For Codex v0.9 Codex CLI Smoke Spec

## Goal

Make the real `--adapter codex-cli` path compatible with the current Codex CLI
`codex exec` argument contract, then prove it with a minimal live smoke that
uses the clone user's own Codex login state.

## Why

v0.8 made clone bootstrap practical, but a real minimal smoke found that the
adapter still passed an old approval-policy flag:

```text
error: unexpected argument '-a' found
```

That blocks the closest clone-and-use path. The adapter must follow the current
`codex exec` shape and keep all authentication on the user's local Codex side.

## Scope

Update the Codex CLI adapter so worker and verifier calls use:

```powershell
codex exec -C <root> -s <sandbox> <prompt>
```

Also update versioned release documentation and plugin metadata to v0.9.

## Non-Goals

- Do not introduce project-owned API keys.
- Do not change live OpenAI Agents SDK behavior.
- Do not remove the adapter's Python configuration surface unless needed for
  compatibility.
- Do not auto-run real workers in `doctor` or `bootstrap`.

## Acceptance Criteria

- Unit tests fail if `-a` is reintroduced into Codex CLI adapter arguments.
- Windows Codex CLI process-cleanup noise is stripped before worker output is
  persisted or verifier verdicts are parsed.
- CLI run commands return non-zero when verifier failures leave synthesis
  incomplete.
- `python -m pytest -v` passes.
- `python -m cdw doctor` still checks readiness without running workers.
- `python -m cdw live-smoke` still reports local readiness without traceback.
- A minimal `python -m cdw run <spec> --adapter codex-cli` uses the user's
  logged-in Codex CLI and reports verifier failures or quota exhaustion without
  traceback.
- README, CHANGELOG, evaluation docs, Python package version, and plugin
  manifest all identify v0.9.
