"""
Atlas Sanctum — Invention Engine  (Phase IV)
Automated discovery workflow:
  OBSERVE → DETECT FRICTION → FIND HIDDEN RESOURCE → RECOMBINE → PROPOSE

Generates InventionProposals from ranked Opportunities + KnowledgeGraph context.
"""
from __future__ import annotations
import logging
from typing import Any

from atlas.core.knowledge.graph import KnowledgeGraph
from atlas.schemas.types import Opportunity, ImpactDomain
from atlas.schemas.phase4 import InventionProposal, PrototypeStatus

log = logging.getLogger("atlas.core.invention")

# Domain → problem framing templates
_PROBLEM_FRAMES: dict[str, str] = {
    "water":         "Insufficient or unreliable access to clean water",
    "energy":        "Unreliable or unaffordable energy supply",
    "agriculture":   "Low crop yield or food insecurity",
    "manufacturing": "Unused productive capacity and unmet local demand",
    "health":        "Inadequate healthcare access or capacity",
    "cities":        "Infrastructure congestion or service gaps",
    "ecology":       "Environmental degradation or resource depletion",
    "economics":     "Latent economic value not yet mobilised",
    "education":     "Knowledge or skill gaps limiting human potential",
}


class InventionEngine:
    def __init__(self, graph: KnowledgeGraph, node_id: str = ""):
        self._graph = graph
        self._node_id = node_id

    def propose(self, opportunity: Opportunity) -> InventionProposal:
        """Generate a structured invention proposal from an opportunity."""
        domain = opportunity.domain.value
        problem = _PROBLEM_FRAMES.get(domain, "Unmet need detected")

        # Gather entity labels contributing to this opportunity
        resources = [
            self._graph.get_entity(eid)
            for eid in opportunity.entity_ids
            if self._graph.get_entity(eid)
        ]
        resource_labels = [e.label for e in resources if e]
        resource_ids = [e.id for e in resources if e]

        solution = self._synthesise_solution(domain, resource_labels)

        proposal = InventionProposal(
            title=f"Invention: {opportunity.title}",
            problem=problem,
            proposed_solution=solution,
            required_resources=resource_labels,
            estimated_impact=self._estimate_impact(opportunity),
            domain=domain,
            status=PrototypeStatus.IDEA,
            opportunity_id=opportunity.id,
            node_id=self._node_id,
            metadata={"opportunity_score": opportunity.score},
        )
        log.info("Invention proposed: [%s] %s", domain, proposal.title)
        return proposal

    def propose_all(self, opportunities: list[Opportunity]) -> list[InventionProposal]:
        return [self.propose(opp) for opp in opportunities]

    # ------------------------------------------------------------------

    def _synthesise_solution(self, domain: str, resources: list[str]) -> str:
        if not resources:
            return f"Apply available resources to address {domain} gap."
        joined = ", ".join(resources[:3])
        return (
            f"Recombine {joined} to create a locally-operated {domain} solution. "
            f"Prototype, test with community, measure outcomes, iterate."
        )

    def _estimate_impact(self, opp: Opportunity) -> str:
        score = opp.score
        if score >= 0.8:
            return "High — strong resource-need alignment, immediate prototyping recommended"
        if score >= 0.5:
            return "Medium — viable with validation; run a small field experiment first"
        return "Low — early signal; gather more data before committing resources"
