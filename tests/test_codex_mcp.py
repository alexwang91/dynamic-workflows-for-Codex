import builtins
import sys
import types
from types import SimpleNamespace

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


def test_live_adapter_runs_worker_through_codex_mcp(monkeypatch, tmp_path):
    calls = {}

    class FakeMCPServerStdio:
        def __init__(self, name, params, client_session_timeout_seconds):
            calls["server_name"] = name
            calls["server_params"] = params
            calls["timeout"] = client_session_timeout_seconds

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

    class FakeAgent:
        def __init__(self, name, instructions, mcp_servers):
            calls["agent_name"] = name
            calls["instructions"] = instructions
            calls["mcp_servers"] = mcp_servers

    class FakeRunner:
        @staticmethod
        async def run(agent, prompt):
            calls["runner_prompt"] = prompt
            return SimpleNamespace(final_output="worker found evidence")

    agents_module = types.ModuleType("agents")
    agents_module.Agent = FakeAgent
    agents_module.Runner = FakeRunner
    mcp_module = types.ModuleType("agents.mcp")
    mcp_module.MCPServerStdio = FakeMCPServerStdio
    agents_module.mcp = mcp_module
    monkeypatch.setitem(sys.modules, "agents", agents_module)
    monkeypatch.setitem(sys.modules, "agents.mcp", mcp_module)

    plan = build_plan("plan", "Review branch")
    adapter = LiveCodexAdapter(root=tmp_path)

    result = adapter.run_worker(plan.work_units[0])

    assert calls["server_params"] == {"command": "codex", "args": ["mcp-server"]}
    assert calls["agent_name"] == "Codex Worker"
    assert "Create a workflow plan for: Review branch" in calls["runner_prompt"]
    assert str(tmp_path) in calls["runner_prompt"]
    assert result.status == "succeeded"
    assert result.raw_output == "worker found evidence"
