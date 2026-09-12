"""
Atlas Sanctum — Built-in Agents

OpportunityScoutAgent  : scans the knowledge graph and ranks opportunities
ImpactReporterAgent    : summarises the impact ledger for a given domain
"""
from __future__ import annotations
from typing import Any

from atlas.core.agents.runtime import Agent
from atlas.core.knowledge.graph import KnowledgeGraph
from atlas.core.opportunity.engine import OpportunityEngine, unused_resource_detector
from atlas.core.opportunity.scorer import rank_opportunities
from atlas.core.impact.ledger import ImpactLedger
from atlas.schemas.types import ImpactDomain


class OpportunityScoutAgent(Agent):
    """
    Scans a KnowledgeGraph for opportunities and returns the top-N ranked.
    Expects context keys:
        graph      : KnowledgeGraph
        node_id    : str
        top_n      : int  (default 5)
    """

    @property
    def name(self) -> str:
        return "opportunity_scout"

    def plan(self, context: dict[str, Any]) -> list[str]:
        return ["scan", "rank", "report"]

    def act(self, action: str, context: dict[str, Any]) -> Any:
        graph: KnowledgeGraph = context["graph"]
        node_id: str = context.get("node_id", "")
        top_n: int = int(context.get("top_n", 5))

        if action == "scan":
            engine = OpportunityEngine(graph, node_id=node_id)
            engine.register(unused_resource_detector)
            opps = engine.scan()
            context["_opps"] = opps
            return {"count": len(opps)}

        if action == "rank":
            opps = context.get("_opps", [])
            ranked = rank_opportunities(opps)
            context["_ranked"] = ranked[:top_n]
            return {"top_n": len(context["_ranked"])}

        if action == "report":
            ranked = context.get("_ranked", [])
            return [
                {"id": o.id, "title": o.title, "domain": o.domain.value, "score": round(o.score, 3)}
                for o in ranked
            ]

        return {}


class ImpactReporterAgent(Agent):
    """
    Summarises the impact ledger.
    Expects context keys:
        ledger  : ImpactLedger
        domain  : str  (optional, ImpactDomain value)
    """

    @property
    def name(self) -> str:
        return "impact_reporter"

    def plan(self, context: dict[str, Any]) -> list[str]:
        return ["summarise"]

    def act(self, action: str, context: dict[str, Any]) -> Any:
        ledger: ImpactLedger = context["ledger"]
        domain_str: str | None = context.get("domain")
        domain = ImpactDomain(domain_str) if domain_str else None

        if action == "summarise":
            records = ledger.query(domain=domain)
            summary = ledger.summary()
            return {
                "total_records": len(records),
                "by_domain": summary,
            }
        return {}
