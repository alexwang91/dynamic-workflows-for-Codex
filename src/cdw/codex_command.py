from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
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
        if _is_windowsapps_codex_package(path_command):
            user_command = _user_codex_command(values)
            if user_command:
                return CodexCommandResolution(command=user_command, source="path")
        return CodexCommandResolution(command=path_command, source="path")

    return CodexCommandResolution(command=None, source="missing")


def _is_windowsapps_codex_package(command: str) -> bool:
    normalized = command.replace("\\", "/").lower()
    return "/windowsapps/openai.codex_" in normalized


def _user_codex_command(env: Mapping[str, str]) -> str | None:
    local_app_data = env.get("LOCALAPPDATA") or os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        return None
    candidate = Path(local_app_data) / "OpenAI" / "Codex" / "bin" / "codex.exe"
    if candidate.exists():
        return str(candidate)
    return None
