from __future__ import annotations

from pathlib import Path


SKILL_NAME = "dynamic-workflows-for-Codex"


def install_skill(root: Path) -> Path:
    path = root / ".agents" / "skills" / SKILL_NAME / "SKILL.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build_skill_content(), encoding="utf-8")
    return path


def build_skill_content(skill_name: str = SKILL_NAME) -> str:
    return f"""---
name: {skill_name}
description: Use when a Codex task needs an external dynamic workflow runtime, including multi-agent review, debugging, resumable workflow specs, or guarded migrations.
---

# Dynamic Workflows For Codex

Use the `cdw` runtime. The runtime owns orchestration, state, worker dispatch, verification, and synthesis.

## First Check

Run `cdw doctor --root <repo>` before real workflows. It verifies local state
writeability, the repo-local plugin package, the packaged skill, and the user's
own Codex CLI without running a real worker or requiring the project author's
API key.

If `codex` is not on PATH, rerun doctor with `--codex-command <path>` or set
`CDW_CODEX_COMMAND`.

## Commands

- Run `cdw plan "<request>" --save-spec <file>` to create a reusable workflow spec.
- Run `cdw review "<request>" --adapter codex-cli` for a real review workflow through the user's logged-in Codex CLI.
- Run `cdw run <workflow-spec> --adapter codex-cli` to execute a saved workflow with Codex CLI workers.
- Run `cdw resume <run-id> --adapter codex-cli` to continue a partial run.
- Run `cdw migrate "<request>" --adapter codex-cli` for guarded migration planning.
- Use `--adapter fake` for deterministic tests and demos.

## Authentication

Prefer `--adapter codex-cli` for clone-and-use workflows. It shells out to the
user's own `codex exec` login state. Do not ask for or assume the project
author's API key.

Use `live-smoke` only when explicitly testing the optional OpenAI Agents SDK
live adapter.

Do not replace the runtime with free-form prompt orchestration.
"""
