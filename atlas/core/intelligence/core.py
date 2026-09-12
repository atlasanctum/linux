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
from atlas.schemas.phase2 import AgentTask, SimulationRun
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
