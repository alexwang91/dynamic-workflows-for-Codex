from __future__ import annotations

from pathlib import Path

from cdw.codex_mcp import CodexAdapter
from cdw.runtime import (
    ensure_verification_results,
    ensure_worker_results,
    finalize_synthesis,
)
from cdw.schemas import RunState
from cdw.state import load_run_state


def resume_run(root: Path, run_id: str, adapter: CodexAdapter) -> RunState:
    state = load_run_state(root, run_id)
    ensure_worker_results(root, state, adapter)
    ensure_verification_results(root, state, adapter)
    finalize_synthesis(root, state)
    return state
