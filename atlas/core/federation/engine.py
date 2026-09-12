"""
Atlas Sanctum — Regional Federation Engine  (Phase V)
Manages cross-node orchestration and regional network membership.
Nodes share anonymised opportunity signals and impact summaries.
Full data sovereignty is preserved — raw data never leaves the origin node.
"""
from __future__ import annotations
import logging
from datetime import datetime
from typing import Any

from atlas.schemas.phase5 import RegionalNetwork
from atlas.schemas.phase3 import SyncEnvelope

log = logging.getLogger("atlas.core.federation")


class FederationEngine:
    def __init__(self, node_id: str):
        self._node_id = node_id
        self._networks: dict[str, RegionalNetwork] = {}
        self._peer_summaries: dict[str, dict] = {}   # node_id → last received summary

    # ------------------------------------------------------------------
    # Network management
    # ------------------------------------------------------------------

    def create_network(self, name: str, region: str) -> RegionalNetwork:
        net = RegionalNetwork(name=name, region=region,
                              member_node_ids=[self._node_id])
        self._networks[net.id] = net
        log.info("Regional network created: %s [%s]", name, region)
        return net

    def join_network(self, network_id: str) -> bool:
        net = self._networks.get(network_id)
        if not net:
            return False
        if self._node_id not in net.member_node_ids:
            net.member_node_ids.append(self._node_id)
            log.info("Node %s joined network %s", self._node_id, net.name)
        return True

    # ------------------------------------------------------------------
    # Cross-node intelligence sharing
    # ------------------------------------------------------------------

    def broadcast_summary(self, summary: dict[str, Any],
                          network_id: str) -> list[SyncEnvelope]:
        """
        Package a node summary (opportunities, impact, graph stats) as
        SyncEnvelopes for each peer in the network.
        Raw data is never included — only aggregated signals.
        """
        net = self._networks.get(network_id)
        if not net:
            return []
        envelopes = []
        for peer_id in net.member_node_ids:
            if peer_id == self._node_id:
                continue
            env = SyncEnvelope(
                origin_node_id=self._node_id,
                target_node_id=peer_id,
                payload_type="node_summary",
                payload={
                    "node_id": self._node_id,
                    "network_id": network_id,
                    "summary": summary,
                    "ts": datetime.utcnow().isoformat() + "Z",
                },
            )
            envelopes.append(env)
        log.info("Broadcasting summary to %d peers in %s",
                 len(envelopes), net.name)
        return envelopes

    def receive_summary(self, envelope: SyncEnvelope) -> None:
        """Accept and store a peer node summary."""
        if envelope.payload_type != "node_summary":
            return
        peer_id = envelope.origin_node_id
        self._peer_summaries[peer_id] = envelope.payload.get("summary", {})
        log.info("Received summary from peer %s", peer_id)

    def network_intelligence(self, network_id: str) -> dict:
        """Aggregate intelligence across all known peers in a network."""
        net = self._networks.get(network_id)
        if not net:
            return {}
        peers = {nid: self._peer_summaries.get(nid, {})
                 for nid in net.member_node_ids}
        return {
            "network": net.name,
            "region": net.region,
            "member_count": len(net.member_node_ids),
            "peers": peers,
        }

    def networks(self) -> list[RegionalNetwork]:
        return list(self._networks.values())
