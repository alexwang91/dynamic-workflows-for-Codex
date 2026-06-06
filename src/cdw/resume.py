from __future__ import annotations

from pathlib import Path

from cdw.codex_mcp import CodexAdapter
from cdw.runtime import execute_existing_state
from cdw.schemas import RunState
from cdw.state import load_run_state


def resume_run(root: Path, run_id: str, adapter: CodexAdapter) -> RunState:
    state = load_run_state(root, run_id)
    return execute_existing_state(root, state, adapter)
