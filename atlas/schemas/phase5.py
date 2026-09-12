"""
Atlas Sanctum — Phase V Schema
Project, CapitalAllocation, MarketplaceListing, RegionalNetwork
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
import uuid


def _uid() -> str:
    return str(uuid.uuid4())


class ProjectStatus(str, Enum):
    PROPOSED = "proposed"
    FUNDED = "funded"
    ACTIVE = "active"
    COMPLETE = "complete"
    CANCELLED = "cancelled"


class ListingStatus(str, Enum):
    OPEN = "open"
    MATCHED = "matched"
    CLOSED = "closed"


@dataclass
class Project:
    """A coordinated initiative with capital, resources, and measurable outcomes."""
    id: str = field(default_factory=_uid)
    title: str = ""
    description: str = ""
    domain: str = ""
    status: ProjectStatus = ProjectStatus.PROPOSED
    lead_node_id: str = ""
    opportunity_id: str = ""
    invention_id: str = ""
    budget_usd: float = 0.0
    allocated_usd: float = 0.0
    target_impact: dict[str, Any] = field(default_factory=dict)
    actual_impact: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CapitalAllocation:
    """A traceable capital allocation to a project."""
    id: str = field(default_factory=_uid)
    project_id: str = ""
    amount_usd: float = 0.0
    source: str = ""              # e.g. "impact_fund", "grant", "enterprise"
    allocated_at: datetime = field(default_factory=datetime.utcnow)
    conditions: str = ""          # human-readable conditions
    human_approved: bool = False
    approver_id: str = ""


@dataclass
class MarketplaceListing:
    """A listing in the Atlas project marketplace — needs, resources, or skills."""
    id: str = field(default_factory=_uid)
    kind: str = ""                # "need" | "resource" | "skill" | "project"
    title: str = ""
    description: str = ""
    domain: str = ""
    node_id: str = ""
    status: ListingStatus = ListingStatus.OPEN
    contact: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RegionalNetwork:
    """A named federation of Atlas nodes sharing intelligence."""
    id: str = field(default_factory=_uid)
    name: str = ""
    region: str = ""
    member_node_ids: list[str] = field(default_factory=list)
    shared_policies: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)
