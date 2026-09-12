"""
Atlas Sanctum — Phase II Schema Extensions
AgentTask, AgentResult, SimulationRun, PolicyRule
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
import uuid


def _uid() -> str:
    return str(uuid.uuid4())


class AgentStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class SimulationStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class AgentTask:
    id: str = field(default_factory=_uid)
    agent_name: str = ""
    intent: str = ""                      # natural-language goal
    context: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    status: AgentStatus = AgentStatus.PENDING


@dataclass
class AgentResult:
    task_id: str = ""
    agent_name: str = ""
    status: AgentStatus = AgentStatus.DONE
    output: dict[str, Any] = field(default_factory=dict)
    completed_at: datetime = field(default_factory=datetime.utcnow)
    error: str = ""


@dataclass
class PolicyRule:
    id: str = field(default_factory=_uid)
    name: str = ""
    description: str = ""
    condition: str = ""           # Python expression evaluated against context
    effect: str = "allow"         # "allow" | "deny"
    priority: int = 0


@dataclass
class SimulationRun:
    id: str = field(default_factory=_uid)
    name: str = ""
    model: str = ""               # name of the registered model
    parameters: dict[str, Any] = field(default_factory=dict)
    status: SimulationStatus = SimulationStatus.PENDING
    result: dict[str, Any] = field(default_factory=dict)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    node_id: str = ""
