"""
Atlas Sanctum — Agent Runtime
Phase II: perceive → plan → act → observe loop.

Agents are registered by name and dispatched tasks via the AgentRuntime.
Each agent receives a task context and returns a structured result.
"""
from __future__ import annotations
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from atlas.schemas.phase2 import AgentTask, AgentResult, AgentStatus

log = logging.getLogger("atlas.core.agents")


# ---------------------------------------------------------------------------
# Base agent
# ---------------------------------------------------------------------------

class Agent(ABC):
    """All Atlas agents inherit from this base."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    def perceive(self, context: dict[str, Any]) -> dict[str, Any]:
        """Filter and enrich the context before planning. Override as needed."""
        return context

    @abstractmethod
    def plan(self, context: dict[str, Any]) -> list[str]:
        """Return an ordered list of action names to execute."""
        ...

    @abstractmethod
    def act(self, action: str, context: dict[str, Any]) -> dict[str, Any]:
        """Execute a single action and return its output."""
        ...

    def run(self, task: AgentTask) -> AgentResult:
        log.info("[%s] starting task %s: %s", self.name, task.id, task.intent)
        try:
            ctx = self.perceive(task.context)
            actions = self.plan(ctx)
            output: dict[str, Any] = {}
            for action in actions:
                log.debug("[%s] action: %s", self.name, action)
                output[action] = self.act(action, ctx)
            return AgentResult(
                task_id=task.id,
                agent_name=self.name,
                status=AgentStatus.DONE,
                output=output,
                completed_at=datetime.utcnow(),
            )
        except Exception as exc:
            log.error("[%s] task %s failed: %s", self.name, task.id, exc)
            return AgentResult(
                task_id=task.id,
                agent_name=self.name,
                status=AgentStatus.FAILED,
                error=str(exc),
                completed_at=datetime.utcnow(),
            )


# ---------------------------------------------------------------------------
# Runtime
# ---------------------------------------------------------------------------

class AgentRuntime:
    def __init__(self):
        self._agents: dict[str, Agent] = {}

    def register(self, agent: Agent) -> None:
        self._agents[agent.name] = agent
        log.info("Agent registered: %s", agent.name)

    def dispatch(self, task: AgentTask) -> AgentResult:
        agent = self._agents.get(task.agent_name)
        if agent is None:
            return AgentResult(
                task_id=task.id,
                agent_name=task.agent_name,
                status=AgentStatus.FAILED,
                error=f"no agent named '{task.agent_name}'",
            )
        task.status = AgentStatus.RUNNING
        result = agent.run(task)
        task.status = result.status
        return result

    def agents(self) -> list[str]:
        return list(self._agents.keys())
