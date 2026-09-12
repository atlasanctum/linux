"""
Atlas Sanctum — Atlas Core
The central orchestrator for Phase II.
Wires together: KnowledgeGraph, OpportunityEngine, AgentRuntime,
PolicyEngine, SimulationEngine, and ImpactLedger.
"""
from __future__ import annotations
import logging
from pathlib import Path
from typing import Any

from atlas.core.knowledge.graph import KnowledgeGraph
from atlas.core.knowledge.store import GraphStore
from atlas.core.opportunity.engine import OpportunityEngine, unused_resource_detector
from atlas.core.opportunity.scorer import rank_opportunities
from atlas.core.agents.runtime import AgentRuntime
from atlas.core.agents.builtins import OpportunityScoutAgent, ImpactReporterAgent
from atlas.core.policy.engine import PolicyEngine, human_oversight_required, data_minimization
from atlas.core.simulation.engine import SimulationEngine, water_demand_model, energy_balance_model
from atlas.core.impact.ledger import ImpactLedger
from atlas.core.invention.engine import InventionEngine
from atlas.core.invention.twins import (
    DigitalTwinEngine, PrototypeManager,
    water_pump_updater, solar_array_updater,
    crop_field_updater, clinic_updater,
    workshop_updater, traffic_junction_updater,
)
from atlas.core.coordination.engine import CoordinationEngine
from atlas.core.coordination.marketplace import Marketplace
from atlas.core.federation.engine import FederationEngine
from atlas.core.globalnet.engine import GlobalNetworkEngine
from atlas.schemas.phase2 import AgentTask, SimulationRun
from atlas.schemas.phase4 import InventionProposal, DigitalTwin
from atlas.schemas.phase5 import Project
from atlas.schemas.phase6 import GlobalNetwork, WorldModelSnapshot, ExchangeKind
from atlas.schemas.types import Opportunity

log = logging.getLogger("atlas.core")


class AtlasCore:
    def __init__(self, node_id: str, data_dir: Path):
        self.node_id = node_id
        self.data_dir = data_dir
        data_dir.mkdir(parents=True, exist_ok=True)

        # Knowledge
        self._store = GraphStore(data_dir / "knowledge_graph.json")
        self.graph: KnowledgeGraph = self._store.load()

        # Opportunity
        self._opp_engine = OpportunityEngine(self.graph, node_id=node_id)
        self._opp_engine.register(unused_resource_detector)

        # Agents
        self.agents = AgentRuntime()
        self.agents.register(OpportunityScoutAgent())
        self.agents.register(ImpactReporterAgent())

        # Policy
        self.policy = PolicyEngine()
        self.policy.register("human_oversight_required", human_oversight_required)
        self.policy.register("data_minimization", data_minimization)

        # Simulation
        self.simulation = SimulationEngine(node_id=node_id)
        self.simulation.register("water_demand", water_demand_model)
        self.simulation.register("energy_balance", energy_balance_model)

        # Impact
        self.impact = ImpactLedger(store_path=data_dir / "impact_ledger.jsonl")

        # Phase IV — Invention
        self.invention = InventionEngine(self.graph, node_id=node_id)
        self.twins = DigitalTwinEngine(node_id=node_id)
        self.twins.register_updater("water_pump", water_pump_updater)
        self.twins.register_updater("solar_array", solar_array_updater)
        self.twins.register_updater("crop_field", crop_field_updater)
        self.twins.register_updater("clinic", clinic_updater)
        self.twins.register_updater("workshop", workshop_updater)
        self.twins.register_updater("traffic_junction", traffic_junction_updater)
        self.prototypes = PrototypeManager(node_id=node_id)

        # Phase V — Coordination
        self.coordination = CoordinationEngine(self.policy, node_id=node_id)
        self.marketplace = Marketplace()
        self.federation = FederationEngine(node_id=node_id)

        # Phase VI — Global Network
        self.global_network = GlobalNetworkEngine(node_id=node_id)

        log.info("AtlasCore initialised [node=%s]", node_id)

    # ------------------------------------------------------------------
    # Knowledge
    # ------------------------------------------------------------------

    def save_graph(self) -> None:
        self._store.save(self.graph)
        log.info("Knowledge graph persisted.")

    # ------------------------------------------------------------------
    # Opportunity
    # ------------------------------------------------------------------

    def scan_opportunities(self, top_n: int = 10) -> list[Opportunity]:
        opps = self._opp_engine.scan()
        return rank_opportunities(opps)[:top_n]

    # ------------------------------------------------------------------
    # Policy gate
    # ------------------------------------------------------------------

    def check_policy(self, policy_name: str, context: dict[str, Any]) -> bool:
        result = self.policy.evaluate(policy_name, context)
        if not result.allowed:
            log.warning("Policy '%s' denied: %s", policy_name, result.reason)
        return result.allowed

    # ------------------------------------------------------------------
    # Agents
    # ------------------------------------------------------------------

    def run_agent(self, agent_name: str, intent: str, context: dict[str, Any]):
        task = AgentTask(agent_name=agent_name, intent=intent, context=context)
        return self.agents.dispatch(task)

    # ------------------------------------------------------------------
    # Simulation
    # ------------------------------------------------------------------

    def simulate(self, model: str, parameters: dict[str, Any], label: str = "") -> SimulationRun:
        return self.simulation.run(model, parameters, label=label)

    # ------------------------------------------------------------------
    # Invention
    # ------------------------------------------------------------------

    def invent(self, top_n: int = 5) -> list[InventionProposal]:
        opps = self.scan_opportunities(top_n=top_n)
        return self.invention.propose_all(opps)

    # ------------------------------------------------------------------
    # Phase VI — Global Network
    # ------------------------------------------------------------------

    def connect_global_network(self, peer_node_id: str,
                                peer_capabilities: list[str] | None = None):
        """Perform interoperability handshake with a remote Atlas node."""
        return self.global_network.handshake(peer_node_id, peer_capabilities)

    def build_world_model(self, network_id: str,
                          regional_summaries: list[dict]) -> WorldModelSnapshot:
        """Aggregate regional summaries into a world model snapshot."""
        return self.global_network.build_world_snapshot(network_id, regional_summaries)

    def publish_research(self, title: str, description: str,
                         network_id: str, payload: dict,
                         tags: list[str] | None = None):
        """Publish a research artefact to the global network."""
        return self.global_network.publish_research(
            ExchangeKind.KNOWLEDGE, title, description,
            network_id, payload, tags
        )
