"""
Atlas Sanctum — Core Schema Types
Phase I: Foundation primitives
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
import uuid


def _uid() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class NodeRole(str, Enum):
    EDGE = "edge"
    COMMUNITY = "community"
    INSTITUTIONAL = "institutional"
    REGIONAL = "regional"
    CLOUD = "cloud"


class SignalSource(str, Enum):
    SENSOR = "sensor"
    HUMAN = "human"
    SATELLITE = "satellite"
    GIS = "gis"
    ENTERPRISE = "enterprise"
    OPEN_DATASET = "open_dataset"
    FIELD_RESEARCH = "field_research"


class OpportunityStatus(str, Enum):
    DETECTED = "detected"
    VALIDATED = "validated"
    ACTIVE = "active"
    CLOSED = "closed"


class ImpactDomain(str, Enum):
    WATER = "water"
    ENERGY = "energy"
    AGRICULTURE = "agriculture"
    HEALTH = "health"
    MANUFACTURING = "manufacturing"
    CITIES = "cities"
    ECOLOGY = "ecology"
    EDUCATION = "education"
    ECONOMICS = "economics"


# ---------------------------------------------------------------------------
# Identity
# ---------------------------------------------------------------------------

@dataclass
class Identity:
    id: str = field(default_factory=_uid)
    public_key: str = ""          # Ed25519 public key (hex)
    name: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------

@dataclass
class NodeConfig:
    id: str = field(default_factory=_uid)
    name: str = ""
    role: NodeRole = NodeRole.EDGE
    location: str = ""            # human-readable or GeoJSON point string
    identity: Identity | None = None
    offline_capable: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Reality signals
# ---------------------------------------------------------------------------

@dataclass
class Signal:
    id: str = field(default_factory=_uid)
    source: SignalSource = SignalSource.SENSOR
    domain: ImpactDomain = ImpactDomain.WATER
    node_id: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    payload: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Knowledge graph primitives
# ---------------------------------------------------------------------------

@dataclass
class Entity:
    id: str = field(default_factory=_uid)
    kind: str = ""                # e.g. "person", "machine", "resource"
    label: str = ""
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class Relation:
    id: str = field(default_factory=_uid)
    source_id: str = ""
    target_id: str = ""
    kind: str = ""                # e.g. "owns", "needs", "produces"
    weight: float = 1.0
    properties: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Opportunity graph
# ---------------------------------------------------------------------------

@dataclass
class Opportunity:
    id: str = field(default_factory=_uid)
    title: str = ""
    domain: ImpactDomain = ImpactDomain.ECONOMICS
    status: OpportunityStatus = OpportunityStatus.DETECTED
    node_id: str = ""
    entity_ids: list[str] = field(default_factory=list)   # contributing entities
    score: float = 0.0            # 0–1 confidence / potential
    detected_at: datetime = field(default_factory=datetime.utcnow)
    description: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Impact ledger entry
# ---------------------------------------------------------------------------

@dataclass
class ImpactRecord:
    id: str = field(default_factory=_uid)
    opportunity_id: str = ""
    domain: ImpactDomain = ImpactDomain.ECONOMICS
    metric: str = ""              # e.g. "households_with_water"
    value: float = 0.0
    unit: str = ""
    measured_at: datetime = field(default_factory=datetime.utcnow)
    node_id: str = ""
    notes: str = ""
