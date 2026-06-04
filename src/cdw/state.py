from __future__ import annotations

import json
import uuid
from pathlib import Path

from cdw.schemas import RunState, WorkflowPlan


def create_run_state(plan: WorkflowPlan) -> RunState:
    return RunState(run_id=uuid.uuid4().hex[:12], plan=plan)


def run_dir(root: Path, run_id: str) -> Path:
    return root / ".cdw" / "runs" / run_id


def save_run_state(root: Path, state: RunState) -> Path:
    directory = run_dir(root, state.run_id)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "state.json"
    tmp_path = directory / "state.json.tmp"
    tmp_path.write_text(state.model_dump_json(indent=2), encoding="utf-8")
    tmp_path.replace(path)
    return path


def load_run_state(root: Path, run_id: str) -> RunState:
    path = run_dir(root, run_id) / "state.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return RunState.model_validate(data)
