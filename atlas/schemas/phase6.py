"""
Atlas Sanctum — Phase VI Schema
GlobalNetwork, WorldModelSnapshot, CivilizationSignal, ResearchExchange
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
import uuid


def _uid() -> str:
    return str(uuid.uuid4())


class NetworkTier(str, Enum):
    COMMUNITY = "community"
    REGIONAL = "regional"
    NATIONAL = "national"
    CONTINENTAL = "continental"
    GLOBAL = "global"


class ExchangeKind(str, Enum):
    KNOWLEDGE = "knowledge"
    MODEL = "model"
    DATASET = "dataset"
    SIMULATION = "simulation"
    PROTOCOL = "protocol"


@dataclass
class GlobalNetwork:
    """A named global federation spanning multiple regional networks."""
    id: str = field(default_factory=_uid)
    name: str = ""
    tier: NetworkTier = NetworkTier.GLOBAL
    regional_network_ids: list[str] = field(default_factory=list)
    member_node_count: int = 0
    shared_protocols: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class WorldModelSnapshot:
    """
    An aggregated snapshot of civilisation-scale signals across the network.
    Never contains raw node data — only anonymised, aggregated statistics.
    """
    id: str = field(default_factory=_uid)
    network_id: str = ""
    contributing_nodes: int = 0
    domain_summaries: dict[str, Any] = field(default_factory=dict)
    # e.g. {"water": {"nodes": 12, "avg_coverage_pct": 67.3}, ...}
    opportunity_count: int = 0
    active_project_count: int = 0
    total_impact_records: int = 0
    snapshot_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ResearchExchange:
    """A cross-node research artefact shared through the global network."""
    id: str = field(default_factory=_uid)
    kind: ExchangeKind = ExchangeKind.KNOWLEDGE
    title: str = ""
    description: str = ""
    origin_node_id: str = ""
    network_id: str = ""
    payload_hash: str = ""        # SHA-256 of the artefact — content travels separately
    tags: list[str] = field(default_factory=list)
    published_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class InteropHandshake:
    """
    Protocol handshake record when two Atlas nodes establish interoperability.
    Stores the negotiated protocol version and capability set.
    """
    id: str = field(default_factory=_uid)
    node_a_id: str = ""
    node_b_id: str = ""
    protocol_version: str = "atlas/interop/v1"
    capabilities: list[str] = field(default_factory=list)
    # e.g. ["sync", "simulation", "marketplace", "federation"]
    established_at: datetime = field(default_factory=datetime.utcnow)
    active: bool = True
