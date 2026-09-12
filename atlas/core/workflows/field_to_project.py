"""
Atlas Sanctum — Field-to-Project Workflow  (Phase V)
The complete coordination loop:
  Field Signal → Opportunity → Invention Proposal → Project → Capital → Impact

This is the primary workflow that connects Phase III field systems
to Phase V economic coordination.
"""
from __future__ import annotations
import logging
from dataclasses import dataclass
from typing import Any

from atlas.core.intelligence.core import AtlasCore
from atlas.core.coordination.engine import CoordinationEngine
from atlas.core.coordination.marketplace import Marketplace
from atlas.schemas.phase4 import InventionProposal
from atlas.schemas.phase5 import Project, MarketplaceListing

log = logging.getLogger("atlas.core.workflows.field_to_project")


@dataclass
class WorkflowResult:
    opportunities_found: int = 0
    proposals_generated: int = 0
    projects_created: int = 0
    listings_published: int = 0
    capital_allocated_usd: float = 0.0


def run_field_to_project(
    core: AtlasCore,
    coordination: CoordinationEngine,
    marketplace: Marketplace,
    approver_id: str,
    capital_per_project_usd: float = 5000.0,
    top_n: int = 3,
) -> WorkflowResult:
    """
    Execute the full field-to-project loop.
    Only creates projects for opportunities scoring above 0.5.
    Capital allocation is always human-approved via policy gate.
    """
    result = WorkflowResult()

    # 1. Scan for opportunities
    opps = core.scan_opportunities(top_n=top_n)
    result.opportunities_found = len(opps)
    log.info("Workflow: %d opportunities found", len(opps))

    # 2. Generate invention proposals
    proposals: list[InventionProposal] = core.invent(top_n=top_n)
    result.proposals_generated = len(proposals)

    # 3. Create projects from high-scoring proposals
    for proposal in proposals:
        opp = next((o for o in opps if o.id == proposal.opportunity_id), None)
        if not opp or opp.score < 0.5:
            continue

        project = coordination.create_project(
            title=proposal.title,
            domain=proposal.domain,
            budget_usd=capital_per_project_usd,
            description=proposal.proposed_solution,
            opportunity_id=proposal.opportunity_id,
            target_impact={"estimated": proposal.estimated_impact},
        )
        result.projects_created += 1

        # 4. Publish to marketplace
        listing = MarketplaceListing(
            kind="project",
            title=project.title,
            description=project.description,
            domain=project.domain,
            node_id=core.node_id,
        )
        marketplace.publish(listing)
        result.listings_published += 1

        # 5. Allocate capital (policy-gated)
        alloc = coordination.allocate_capital(
            project_id=project.id,
            amount_usd=capital_per_project_usd,
            source="atlas_impact_fund",
            approver_id=approver_id,
            conditions="Milestone-based disbursement with impact measurement",
        )
        if alloc:
            result.capital_allocated_usd += alloc.amount_usd
            coordination.activate_project(project.id)

    log.info(
        "Workflow complete: %d projects created, $%.0f allocated",
        result.projects_created, result.capital_allocated_usd,
    )
    return result
