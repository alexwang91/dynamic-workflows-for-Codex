from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path

from cdw.schemas import RunState, WorkflowPlan, WorkflowProcedure


def create_run_state(
    plan: WorkflowPlan,
    procedure: WorkflowProcedure | None = None,
    adapter: str | None = None,
) -> RunState:
    return RunState(
        run_id=uuid.uuid4().hex[:12],
        plan=plan,
        procedure=procedure,
        adapter=adapter,
    )


def run_dir(root: Path, run_id: str) -> Path:
    return root / ".cdw" / "runs" / run_id


def save_run_state(root: Path, state: RunState) -> Path:
    directory = run_dir(root, state.run_id)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "state.json"
    tmp_path = directory / f"state.json.{uuid.uuid4().hex}.tmp"
    tmp_path.write_text(state.model_dump_json(indent=2), encoding="utf-8")
    _replace_with_retry(tmp_path, path)
    return path


def load_run_state(root: Path, run_id: str) -> RunState:
    path = run_dir(root, run_id) / "state.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return RunState.model_validate(data)


def _replace_with_retry(src: Path, dst: Path, attempts: int = 5) -> None:
    for attempt in range(attempts):
        try:
            os.replace(src, dst)
            return
        except PermissionError:
            if attempt == attempts - 1:
                raise
            time.sleep(0.05 * (attempt + 1))
