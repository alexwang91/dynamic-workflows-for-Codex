import builtins

import pytest

from cdw.codex_mcp import LiveCodexAdapter
from cdw.planner import build_plan


def test_live_adapter_has_clear_missing_dependency_error(monkeypatch):
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "agents":
            raise ImportError("missing agents")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    plan = build_plan("plan", "Review branch")
    adapter = LiveCodexAdapter(root=".")

    with pytest.raises(RuntimeError, match="openai-agents"):
        adapter.run_worker(plan.work_units[0])
