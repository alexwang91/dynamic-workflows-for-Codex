# Dynamic Workflows For Codex v0.16 Structured Write Contract Spec

## Goal

Make guarded/write-heavy migration planning produce a machine-readable write
contract before any later write phase can safely exist.

## Why

v0.15 made path boundaries executable, but it still accepts paths extracted from
free-form stage output. That is good enough for a planning guard, but too loose
for future write-heavy migration execution. v0.16 tightens the contract without
executing patches: guarded/write-heavy stages can require a structured
`WRITE_CONTRACT` section, and generated migration workflows require it by
default.

## Scope

Structured contract format:

```text
WRITE_CONTRACT:
{
  "paths": [
    {
      "path": "src/users.py",
      "action": "modify",
      "reason": "Rename User references to Account"
    }
  ],
  "checks": ["python -m pytest tests/test_users.py"]
}
```

- `paths` is required for a valid contract and each entry must include `path`.
- `action` is optional and defaults to `modify`.
- `reason` is optional and defaults to an empty string.
- `checks` is optional and records planned verification commands.
- Legacy `WRITE_PATHS:` remains supported for non-strict workflows.

Runtime behavior:

- Add `requires_write_contract` to workflow constraints, defaulting to `False`.
- Generated migration specs set `requires_write_contract=True`.
- Guarded/write-heavy stages with that flag must emit at least one structured
  contract path.
- Boundary checks validate structured contract paths against
  `allowed_paths`/`forbidden_paths`.
- If a required contract is missing or empty, the boundary result fails before
  artifact writing and synthesis becomes incomplete.
- When a required contract exists, the runtime records whether the contract was
  required/found and stores the parsed path intents in the boundary result.

Prompting and artifacts:

- Runtime appends a concise `WRITE_CONTRACT` instruction to guarded/write-heavy
  stage worker prompts when the workflow requires one.
- Migration patch-planner prompts and expected output explicitly require the
  structured contract.
- The migration plan-review stage produces a `write path contract` artifact
  alongside the guarded patch plan and risk review.

Non-goals:

- Do not execute patches.
- Do not infer write contracts from arbitrary prose.
- Do not break existing read-only/review/debug workflows.
- Do not require structured contracts for legacy specs unless the constraint
  flag is set.

## Acceptance Criteria

- Structured `WRITE_CONTRACT` JSON is parsed from worker summary, raw output, or
  evidence.
- Required contracts fail clearly when missing or empty.
- Structured paths still reject forbidden, outside-allowed, absolute, and parent
  traversal paths.
- Runtime prompts guarded/write-heavy workers for the contract when required.
- Generated migration specs require write contracts and produce a contract
  artifact.
- Status JSON exposes required/found contract state through boundary results.
- Docs, plugin metadata, packaged skill, and version metadata are bumped to
  `0.16.0`.
- Full tests pass.
