from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from cdw.schemas import (
    VerificationResult,
    VerificationStatus,
    WorkerResult,
    WorkerStatus,
    WorkUnit,
)


class CodexAdapter(Protocol):
    def run_worker(self, work_unit: WorkUnit) -> WorkerResult:
        ...

    def verify_worker_result(self, result: WorkerResult) -> VerificationResult:
        ...


@dataclass
class FakeCodexAdapter:
    fail_work_unit_ids: set[str] = field(default_factory=set)

    def run_worker(self, work_unit: WorkUnit) -> WorkerResult:
        if work_unit.id in self.fail_work_unit_ids:
            return WorkerResult(
                work_unit_id=work_unit.id,
                status=WorkerStatus.FAILED,
                summary=f"{work_unit.id} failed",
                evidence=[],
                raw_output="simulated failure",
            )
        return WorkerResult(
            work_unit_id=work_unit.id,
            status=WorkerStatus.SUCCEEDED,
            summary=f"{work_unit.role} completed {work_unit.goal}",
            evidence=[work_unit.expected_output],
            raw_output=f"fake output for {work_unit.id}",
        )

    def verify_worker_result(self, result: WorkerResult) -> VerificationResult:
        if result.status == WorkerStatus.SUCCEEDED and result.evidence:
            return VerificationResult(
                work_unit_id=result.work_unit_id,
                status=VerificationStatus.PASSED,
                notes="Evidence present.",
            )
        return VerificationResult(
            work_unit_id=result.work_unit_id,
            status=VerificationStatus.FAILED,
            notes="Worker failed or returned no evidence.",
        )


@dataclass
class LiveCodexAdapter:
    root: str | Path
    sandbox: str = "workspace-write"
    approval_policy: str = "never"
    timeout_seconds: int = 360000

    def run_worker(self, work_unit: WorkUnit) -> WorkerResult:
        output = self._run_agent(
            agent_name="Codex Worker",
            task_prompt=self._worker_task_prompt(work_unit),
        )
        return WorkerResult(
            work_unit_id=work_unit.id,
            status=WorkerStatus.SUCCEEDED,
            summary=output,
            evidence=[output],
            raw_output=output,
        )

    def verify_worker_result(self, result: WorkerResult) -> VerificationResult:
        output = self._run_agent(
            agent_name="Codex Verifier",
            task_prompt=self._verifier_task_prompt(result),
        )
        first_line = output.strip().splitlines()[0].upper() if output.strip() else ""
        if first_line.startswith("PASSED"):
            return VerificationResult(
                work_unit_id=result.work_unit_id,
                status=VerificationStatus.PASSED,
                notes=output,
            )
        return VerificationResult(
            work_unit_id=result.work_unit_id,
            status=VerificationStatus.FAILED,
            notes=output or "Verifier returned no output.",
        )

    def _run_agent(self, agent_name: str, task_prompt: str) -> str:
        try:
            from agents import Agent, Runner
            from agents.mcp import MCPServerStdio
        except ImportError as exc:
            raise RuntimeError(
                "Live Codex MCP mode requires the optional 'live' dependencies: "
                "openai-agents, openai, and python-dotenv. Install with: "
                "pip install 'codex-dynamic-workflows[live]'."
            ) from exc
        return asyncio.run(
            self._run_agent_async(agent_name, task_prompt, Agent, Runner, MCPServerStdio)
        )

    async def _run_agent_async(
        self,
        agent_name: str,
        task_prompt: str,
        agent_cls,
        runner_cls,
        server_cls,
    ) -> str:
        async with server_cls(
            name="Codex CLI",
            params={"command": "codex", "args": ["mcp-server"]},
            client_session_timeout_seconds=self.timeout_seconds,
        ) as codex_mcp_server:
            agent = agent_cls(
                name=agent_name,
                instructions=(
                    "You are a workflow coordinator. Use the Codex MCP server "
                    "to run exactly one scoped Codex worker session. Return only "
                    "the worker's final answer."
                ),
                mcp_servers=[codex_mcp_server],
            )
            result = await runner_cls.run(agent, self._codex_mcp_instruction(task_prompt))
            return str(getattr(result, "final_output", result))

    def _codex_mcp_instruction(self, task_prompt: str) -> str:
        return (
            "Call the Codex MCP `codex` tool with these arguments:\n"
            f"- prompt: {task_prompt}\n"
            f"- cwd: {Path(self.root)}\n"
            f"- sandbox: {self.sandbox}\n"
            f"- approval-policy: {self.approval_policy}\n"
            "After the tool returns, output only the Codex result content."
        )

    def _worker_task_prompt(self, work_unit: WorkUnit) -> str:
        return (
            f"Role: {work_unit.role}\n"
            f"Goal: {work_unit.goal}\n"
            f"Task: {work_unit.prompt}\n"
            f"Expected output: {work_unit.expected_output}\n"
            "Return a concise structured result with evidence."
        )

    def _verifier_task_prompt(self, result: WorkerResult) -> str:
        return (
            "Verify this worker result adversarially.\n"
            "First line must be exactly `PASSED` or `FAILED`.\n"
            f"Worker result status: {result.status}\n"
            f"Summary: {result.summary}\n"
            f"Evidence: {result.evidence}\n"
            f"Raw output: {result.raw_output}\n"
        )
