from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from typing import Literal, Mapping


CommandSource = Literal["cli", "env", "path", "missing"]


@dataclass(frozen=True)
class CodexCommandResolution:
    command: str | None
    source: CommandSource


def resolve_codex_command(
    explicit: str | None = None,
    env: Mapping[str, str] | None = None,
) -> CodexCommandResolution:
    if explicit:
        return CodexCommandResolution(command=explicit, source="cli")

    values = os.environ if env is None else env
    env_command = values.get("CDW_CODEX_COMMAND")
    if env_command:
        return CodexCommandResolution(command=env_command, source="env")

    path_command = shutil.which("codex")
    if path_command:
        return CodexCommandResolution(command=path_command, source="path")

    return CodexCommandResolution(command=None, source="missing")
