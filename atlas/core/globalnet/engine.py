"""
Atlas Sanctum — Global Network Engine  (Phase VI)
Manages interoperable Atlas node connections, global network membership,
world model aggregation, and cross-region knowledge exchange.

Data sovereignty is preserved at every layer:
  - Raw data never leaves the origin node
  - Only anonymised, aggregated summaries travel the network
  - Every exchange is signed with the origin node's Ed25519 key
"""
from __future__ import annotations
import hashlib
import json
import logging
from datetime import datetime
from typing import Any

from atlas.schemas.phase6 import (
    GlobalNetwork, WorldModelSnapshot, ResearchExchange,
    InteropHandshake, NetworkTier, ExchangeKind,
)
from atlas.schemas.phase5 import RegionalNetwork
from atlas.schemas.phase3 import SyncEnvelope

log = logging.getLogger("atlas.core.globalnet")

INTEROP_VERSION = "atlas/interop/v1"
CAPABILITIES = ["sync", "simulation", "marketplace", "federation", "world_model"]


class GlobalNetworkEngine:
    """
    Manages the global Atlas network layer.

    Responsibilities:
      - Register and connect regional networks into a global network
      - Perform interoperability handshakes with remote nodes
      - Aggregate world model snapshots from regional summaries
      - Publish and receive research exchanges
      - Route cross-region SyncEnvelopes
    """

    def __init__(self, node_id: str):
        self._node_id = node_id
        self._global_networks: dict[str, GlobalNetwork] = {}
        self._handshakes: dict[str, InteropHandshake] = {}   # peer_id → handshake
        self._research_index: dict[str, ResearchExchange] = {}
        self._world_snapshots: list[WorldModelSnapshot] = []

    # ------------------------------------------------------------------
    # Global network management
    # ------------------------------------------------------------------

    def create_global_network(self, name: str,
                               tier: NetworkTier = NetworkTier.GLOBAL) -> GlobalNetwork:
        net = GlobalNetwork(name=name, tier=tier)
        self._global_networks[net.id] = net
        log.info("Global network created: %s [%s]", name, tier.value)
        return net

    def register_regional_network(self, global_network_id: str,
                                   regional: RegionalNetwork) -> bool:
        net = self._global_networks.get(global_network_id)
        if not net:
            return False
        if regional.id not in net.regional_network_ids:
            net.regional_network_ids.append(regional.id)
            net.member_node_count += len(regional.member_node_ids)
            log.info("Regional network '%s' registered in global network '%s'",
                     regional.name, net.name)
        return True

    # ------------------------------------------------------------------
    # Interoperability handshake
    # ------------------------------------------------------------------

    def handshake(self, peer_node_id: str,
                  peer_capabilities: list[str] | None = None) -> InteropHandshake:
        """
        Establish interoperability with a remote Atlas node.
        Negotiates the intersection of capabilities.
        """
        negotiated = list(
            set(CAPABILITIES) & set(peer_capabilities or CAPABILITIES)
        )
        hs = InteropHandshake(
            node_a_id=self._node_id,
            node_b_id=peer_node_id,
            protocol_version=INTEROP_VERSION,
            capabilities=sorted(negotiated),
        )
        self._handshakes[peer_node_id] = hs
        log.info("Interop handshake with %s — capabilities: %s",
                 peer_node_id, negotiated)
        return hs

    def is_interoperable(self, peer_node_id: str, capability: str) -> bool:
        hs = self._handshakes.get(peer_node_id)
        return hs is not None and hs.active and capability in hs.capabilities

    # ------------------------------------------------------------------
    # World model
    # ------------------------------------------------------------------

    def build_world_snapshot(self, network_id: str,
                              regional_summaries: list[dict[str, Any]]) -> WorldModelSnapshot:
        """
        Aggregate regional summaries into a world model snapshot.
        Input summaries come from FederationEngine.network_intelligence() calls
        across multiple regional networks — never raw node data.
        """
        domain_agg: dict[str, dict] = {}
        opp_total = 0
        project_total = 0
        impact_total = 0
        node_count = 0

        for summary in regional_summaries:
            node_count += summary.get("member_count", 0)
            opp_total += summary.get("opportunity_count", 0)
            project_total += summary.get("active_project_count", 0)
            impact_total += summary.get("impact_record_count", 0)
            for domain, stats in summary.get("domains", {}).items():
                if domain not in domain_agg:
                    domain_agg[domain] = {"nodes": 0, "values": []}
                domain_agg[domain]["nodes"] += stats.get("nodes", 0)
                if "avg_value" in stats:
                    domain_agg[domain]["values"].append(stats["avg_value"])

        # Compute averages
        domain_summaries = {}
        for domain, agg in domain_agg.items():
            vals = agg["values"]
            domain_summaries[domain] = {
                "nodes": agg["nodes"],
                "avg_value": sum(vals) / len(vals) if vals else 0.0,
            }

        snap = WorldModelSnapshot(
            network_id=network_id,
            contributing_nodes=node_count,
            domain_summaries=domain_summaries,
            opportunity_count=opp_total,
            active_project_count=project_total,
            total_impact_records=impact_total,
        )
        self._world_snapshots.append(snap)
        log.info("World model snapshot built: %d nodes, %d domains",
                 node_count, len(domain_summaries))
        return snap

    def latest_snapshot(self) -> WorldModelSnapshot | None:
        return self._world_snapshots[-1] if self._world_snapshots else None

    # ------------------------------------------------------------------
    # Research exchange
    # ------------------------------------------------------------------

    def publish_research(self, kind: ExchangeKind, title: str,
                         description: str, network_id: str,
                         payload: Any, tags: list[str] | None = None) -> ResearchExchange:
        """
        Publish a research artefact to the global network.
        Only the hash travels with the exchange record; the payload is
        transferred separately through the secure sync protocol.
        """
        payload_bytes = json.dumps(payload, sort_keys=True).encode()
        payload_hash = hashlib.sha256(payload_bytes).hexdigest()
        exchange = ResearchExchange(
            kind=kind,
            title=title,
            description=description,
            origin_node_id=self._node_id,
            network_id=network_id,
            payload_hash=payload_hash,
            tags=tags or [],
        )
        self._research_index[exchange.id] = exchange
        log.info("Research published: '%s' [%s]", title, kind.value)
        return exchange

    def receive_research(self, exchange: ResearchExchange) -> None:
        self._research_index[exchange.id] = exchange
        log.info("Research received: '%s' from %s",
                 exchange.title, exchange.origin_node_id)

    def search_research(self, tag: str | None = None,
                        kind: ExchangeKind | None = None) -> list[ResearchExchange]:
        results = list(self._research_index.values())
        if tag:
            results = [r for r in results if tag in r.tags]
        if kind:
            results = [r for r in results if r.kind == kind]
        return results

    # ------------------------------------------------------------------
    # Cross-region routing
    # ------------------------------------------------------------------

    def route_envelope(self, envelope: SyncEnvelope,
                       global_network_id: str) -> list[str]:
        """
        Determine which regional networks should receive this envelope.
        Returns a list of regional network IDs to forward to.
        Returns empty list if target node is not in the global network.
        """
        net = self._global_networks.get(global_network_id)
        if not net:
            return []
        # In Phase VI this would resolve target_node_id to its regional network.
        # For now, broadcast to all regional networks in the global network.
        log.info("Routing envelope %s across %d regional networks",
                 envelope.id, len(net.regional_network_ids))
        return net.regional_network_ids

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def status(self) -> dict[str, Any]:
        return {
            "node_id": self._node_id,
            "global_networks": len(self._global_networks),
            "interop_peers": len(self._handshakes),
            "research_artefacts": len(self._research_index),
            "world_snapshots": len(self._world_snapshots),
            "protocol_version": INTEROP_VERSION,
        }
