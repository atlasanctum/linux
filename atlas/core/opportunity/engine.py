"""
Atlas Sanctum — Opportunity Engine
Scans the knowledge graph for latent opportunities by matching
need→resource patterns. Extensible with domain-specific detectors.
"""
from __future__ import annotations
import logging
from typing import Callable

from atlas.core.knowledge.graph import KnowledgeGraph
from atlas.schemas.types import Opportunity, ImpactDomain, OpportunityStatus

log = logging.getLogger("atlas.core.opportunity")

# A detector is a callable that receives the graph and yields Opportunity objects
Detector = Callable[[KnowledgeGraph], list[Opportunity]]


class OpportunityEngine:
    def __init__(self, graph: KnowledgeGraph, node_id: str = ""):
        self._graph = graph
        self._node_id = node_id
        self._detectors: list[Detector] = []
        self._opportunities: dict[str, Opportunity] = {}

    def register(self, detector: Detector) -> None:
        self._detectors.append(detector)

    def scan(self) -> list[Opportunity]:
        found: list[Opportunity] = []
        for detector in self._detectors:
            results = detector(self._graph)
            for opp in results:
                opp.node_id = self._node_id
                self._opportunities[opp.id] = opp
                found.append(opp)
                log.info("Opportunity detected: [%s] %s (score=%.2f)",
                         opp.domain.value, opp.title, opp.score)
        return found

    def all(self) -> list[Opportunity]:
        return list(self._opportunities.values())


# ---------------------------------------------------------------------------
# Built-in detector: unused resource + unmet need in same domain
# ---------------------------------------------------------------------------

def unused_resource_detector(graph: KnowledgeGraph) -> list[Opportunity]:
    """
    Detects when an 'unused_resource' entity and a 'need' entity share
    a common domain property — a basic recombination signal.
    """
    opportunities: list[Opportunity] = []
    resources = {e.id: e for e in graph.find_entities("unused_resource")}
    needs = list(graph.find_entities("need"))

    for need in needs:
        need_domain = need.properties.get("domain")
        for res_id, res in resources.items():
            if res.properties.get("domain") == need_domain:
                opp = Opportunity(
                    title=f"Match: {res.label} → {need.label}",
                    domain=ImpactDomain(need_domain) if need_domain in ImpactDomain._value2member_map_ else ImpactDomain.ECONOMICS,
                    status=OpportunityStatus.DETECTED,
                    entity_ids=[res_id, need.id],
                    score=0.6,
                    description=f"Unused resource '{res.label}' may address need '{need.label}'",
                )
                opportunities.append(opp)
    return opportunities
