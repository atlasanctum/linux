"""
Atlas Sanctum — Opportunity Scorer
Ranks Opportunity objects using a weighted multi-factor model.

Factors (all 0–1, configurable weights):
  - resource_availability  : how available is the matched resource?
  - need_urgency           : how urgent is the need?
  - feasibility            : estimated ease of execution
  - impact_potential       : estimated magnitude of real-world change
"""
from __future__ import annotations
from dataclasses import dataclass, field

from atlas.schemas.types import Opportunity


@dataclass
class ScoringWeights:
    resource_availability: float = 0.25
    need_urgency: float = 0.30
    feasibility: float = 0.20
    impact_potential: float = 0.25


def score_opportunity(opp: Opportunity, weights: ScoringWeights | None = None) -> float:
    """
    Compute a 0–1 composite score from factors stored in opp.metadata.
    Falls back to the existing opp.score if factors are absent.
    """
    w = weights or ScoringWeights()
    m = opp.metadata

    ra = float(m.get("resource_availability", opp.score))
    nu = float(m.get("need_urgency", opp.score))
    fe = float(m.get("feasibility", opp.score))
    ip = float(m.get("impact_potential", opp.score))

    return (
        w.resource_availability * ra
        + w.need_urgency * nu
        + w.feasibility * fe
        + w.impact_potential * ip
    )


def rank_opportunities(
    opportunities: list[Opportunity],
    weights: ScoringWeights | None = None,
) -> list[Opportunity]:
    """Return opportunities sorted by composite score descending, mutating .score in place."""
    for opp in opportunities:
        opp.score = score_opportunity(opp, weights)
    return sorted(opportunities, key=lambda o: o.score, reverse=True)
