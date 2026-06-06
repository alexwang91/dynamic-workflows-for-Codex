# Dynamic Workflows For Codex v0.8 Bootstrap Install Spec

## Goal

Add a clone-user bootstrap command that refreshes the repo-local Codex plugin
package and tells the user exactly how to register and verify it.

## Why

`cdw doctor` tells users what is ready or missing, and `package-plugin
--repo-marketplace` can generate the repo-local plugin package. Clone users
still need a more obvious "start here" command that prepares the repository and
prints the next install steps.

## Scope

Add:

```powershell
python -m cdw bootstrap --root .
```

The command should:

- Generate or refresh `.agents/plugins/marketplace.json`.
- Generate or refresh `.agents/plugins/plugins/dynamic-workflows-for-codex`.
- Print the marketplace path.
- Print the plugin path.
- Print the next commands:
  - `codex plugin marketplace add .agents/plugins`
  - `python -m cdw doctor`
- Avoid running real Codex workers.
- Avoid changing global Codex configuration directly.

## Non-Goals

- Do not call `codex plugin marketplace add` automatically.
- Do not run real `codex exec` workers.
- Do not ask for API keys.
- Do not replace `cdw doctor`; bootstrap prepares files, doctor diagnoses the
  environment.

## Acceptance Criteria

- `cdw bootstrap --root <repo>` writes the repo-local marketplace and plugin
  package.
- The command output includes `marketplace`, `plugin`, `next`, and `doctor`
  lines.
- Tests verify bootstrap behavior without needing Codex installed.
- README and consumer install docs use bootstrap before doctor.
- Full tests pass and a clean clone can install, test, bootstrap, and doctor.
