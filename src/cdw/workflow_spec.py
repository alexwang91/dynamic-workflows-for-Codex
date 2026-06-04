from __future__ import annotations

import json
from pathlib import Path

from cdw.schemas import WorkflowPlan


def save_workflow_spec(path: Path, plan: WorkflowPlan) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(plan.model_dump_json(indent=2), encoding="utf-8")
    return path


def load_workflow_spec(path: Path) -> WorkflowPlan:
    data = json.loads(path.read_text(encoding="utf-8"))
    return WorkflowPlan.model_validate(data)
