from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from pydantic import ValidationError

from cdw.schemas import RunState
from cdw.state import load_run_state, run_dir


@dataclass(frozen=True)
class RunSummary:
    run_id: str
    status: str
    command: str
    request: str
    adapter: str | None
    pending_human_approval: str | None
    worker_count: int
    verification_count: int
    state_path: str
    resume_command: str | None

    def to_dict(self) -> dict:
        return asdict(self)


def summarize_run(root: Path, run_id: str) -> RunSummary:
    state_path = run_dir(root, run_id) / "state.json"
    if not state_path.exists():
        raise RuntimeError(f"run not found: {run_id}")
    state = load_run_state(root, run_id)
    return summarize_state(root, state)


def summarize_state(root: Path, state: RunState) -> RunSummary:
    status = state.synthesis.status if state.synthesis is not None else "unknown"
    resume_command = None
    if state.pending_human_approval is not None:
        adapter_part = f" --adapter {state.adapter}" if state.adapter else ""
        resume_command = (
            f"python -m cdw resume {state.run_id}"
            f"{adapter_part} --approve-human-gates"
        )
    return RunSummary(
        run_id=state.run_id,
        status=status,
        command=state.plan.command.value,
        request=state.plan.request,
        adapter=state.adapter,
        pending_human_approval=state.pending_human_approval,
        worker_count=len(state.worker_results),
        verification_count=len(state.verification_results),
        state_path=str(run_dir(root, state.run_id) / "state.json"),
        resume_command=resume_command,
    )


def list_run_summaries(root: Path) -> list[RunSummary]:
    runs_dir = root / ".cdw" / "runs"
    if not runs_dir.exists():
        return []

    state_paths = sorted(
        runs_dir.glob("*/state.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    summaries = []
    for state_path in state_paths:
        try:
            summaries.append(summarize_run(root, state_path.parent.name))
        except (OSError, ValueError, ValidationError):
            continue
    return summaries
