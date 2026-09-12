"""
Atlas Sanctum — Economic Coordination Engine  (Phase V)
Manages the capital → projects → infrastructure → outcomes → reinvestment loop.

Capital allocation is policy-gated: no autonomous allocation without human approval.
"""
from __future__ import annotations
import logging
from datetime import datetime
from typing import Any

from atlas.core.policy.engine import PolicyEngine
from atlas.schemas.phase5 import Project, CapitalAllocation, ProjectStatus
from atlas.schemas.types import ImpactDomain

log = logging.getLogger("atlas.core.coordination")


class CoordinationEngine:
    def __init__(self, policy: PolicyEngine, node_id: str = ""):
        self._policy = policy
        self._node_id = node_id
        self._projects: dict[str, Project] = {}
        self._allocations: list[CapitalAllocation] = []

    # ------------------------------------------------------------------
    # Projects
    # ------------------------------------------------------------------

    def create_project(self, title: str, domain: str, budget_usd: float,
                       description: str = "", opportunity_id: str = "",
                       target_impact: dict[str, Any] | None = None) -> Project:
        project = Project(
            title=title, description=description, domain=domain,
            budget_usd=budget_usd, lead_node_id=self._node_id,
            opportunity_id=opportunity_id,
            target_impact=target_impact or {},
        )
        self._projects[project.id] = project
        log.info("Project created: [%s] %s (budget=$%.0f)", domain, title, budget_usd)
        return project

    def activate_project(self, project_id: str) -> bool:
        project = self._projects.get(project_id)
        if not project:
            return False
        if project.allocated_usd < project.budget_usd * 0.5:
            log.warning("Project %s cannot activate: insufficient funding (%.0f/%.0f)",
                        project_id, project.allocated_usd, project.budget_usd)
            return False
        project.status = ProjectStatus.ACTIVE
        project.updated_at = datetime.utcnow()
        log.info("Project activated: %s", project.title)
        return True

    def complete_project(self, project_id: str,
                         actual_impact: dict[str, Any]) -> bool:
        project = self._projects.get(project_id)
        if not project:
            return False
        project.status = ProjectStatus.COMPLETE
        project.actual_impact = actual_impact
        project.updated_at = datetime.utcnow()
        log.info("Project complete: %s | impact: %s", project.title, actual_impact)
        return True

    # ------------------------------------------------------------------
    # Capital — always policy-gated
    # ------------------------------------------------------------------

    def allocate_capital(self, project_id: str, amount_usd: float,
                         source: str, approver_id: str,
                         conditions: str = "") -> CapitalAllocation | None:
        # Policy gate — no autonomous capital allocation
        ctx = {
            "action_type": "capital_allocation",
            "amount_usd": amount_usd,
            "impact_level": "high" if amount_usd > 10_000 else "medium",
            "human_approved": bool(approver_id),
            "node_id": self._node_id,
        }
        result = self._policy.evaluate("human_oversight_required", ctx)
        if not result.allowed:
            log.warning("Capital allocation denied by policy: %s", result.reason)
            return None

        project = self._projects.get(project_id)
        if not project:
            log.warning("Capital allocation failed: project %s not found", project_id)
            return None

        alloc = CapitalAllocation(
            project_id=project_id, amount_usd=amount_usd,
            source=source, approver_id=approver_id,
            conditions=conditions, human_approved=True,
        )
        self._allocations.append(alloc)
        project.allocated_usd += amount_usd
        project.updated_at = datetime.utcnow()
        log.info("Capital allocated: $%.0f → %s (from %s)", amount_usd, project.title, source)
        return alloc

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def projects(self, status: ProjectStatus | None = None) -> list[Project]:
        if status:
            return [p for p in self._projects.values() if p.status == status]
        return list(self._projects.values())

    def total_allocated(self) -> float:
        return sum(a.amount_usd for a in self._allocations)

    def impact_summary(self) -> dict:
        completed = [p for p in self._projects.values()
                     if p.status == ProjectStatus.COMPLETE]
        return {
            "total_projects": len(self._projects),
            "active": len([p for p in self._projects.values()
                           if p.status == ProjectStatus.ACTIVE]),
            "complete": len(completed),
            "total_allocated_usd": self.total_allocated(),
            "outcomes": [p.actual_impact for p in completed],
        }
