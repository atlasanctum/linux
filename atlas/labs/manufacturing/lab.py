"""
Atlas Sanctum — Manufacturing Field Lab
Idle machines + waste materials → Opportunity Graph → Local production opportunity
"""
from __future__ import annotations
import logging
from pathlib import Path

from atlas.core.intelligence.core import AtlasCore
from atlas.core.gis.index import GeoIndex, GeoFeature
from atlas.schemas.types import Entity, Relation, ImpactRecord, ImpactDomain
from atlas.schemas.phase3 import GeoPoint

log = logging.getLogger("atlas.labs.manufacturing")


def run_manufacturing_lab(data_dir: Path, node_id: str = "mfg-lab-node") -> dict:
    core = AtlasCore(node_id=node_id, data_dir=data_dir)
    geo = GeoIndex()

    workshop = GeoPoint(latitude=-1.3167, longitude=36.8833)
    geo.add(GeoFeature(
        id="workshop-001", kind="facility",
        label="Gikomba Workshop", location=workshop,
        properties={"type": "metal_fabrication"},
    ))

    # Populate knowledge graph with real-world entities
    entities = [
        Entity(id="m1", kind="unused_resource", label="Idle Metal Lathe",
               properties={"domain": "manufacturing", "availability": 0.8, "location": "Gikomba"}),
        Entity(id="m2", kind="unused_resource", label="Scrap Steel Stock",
               properties={"domain": "manufacturing", "availability": 0.9, "location": "Gikomba"}),
        Entity(id="s1", kind="skill", label="Welding Expertise",
               properties={"domain": "manufacturing", "workers": 3}),
        Entity(id="n1", kind="need", label="Affordable Roofing Brackets",
               properties={"domain": "manufacturing", "urgency": 0.85, "market_size": 500}),
        Entity(id="n2", kind="need", label="Water Tank Fittings",
               properties={"domain": "manufacturing", "urgency": 0.75, "market_size": 300}),
    ]
    for e in entities:
        core.graph.add_entity(e)

    core.graph.add_relation(Relation(source_id="m1", target_id="n1", kind="can_produce"))
    core.graph.add_relation(Relation(source_id="m2", target_id="n1", kind="material_for"))
    core.graph.add_relation(Relation(source_id="s1", target_id="n1", kind="skill_for"))
    core.graph.add_relation(Relation(source_id="m1", target_id="n2", kind="can_produce"))

    opps = core.scan_opportunities(top_n=5)

    for opp in opps:
        opp.metadata = {
            "resource_availability": 0.85,
            "need_urgency": 0.80,
            "feasibility": 0.75,
            "impact_potential": 0.70,
        }

    core.impact.record(ImpactRecord(
        domain=ImpactDomain.MANUFACTURING,
        metric="opportunities_detected",
        value=len(opps),
        unit="opportunities",
        node_id=node_id,
        notes="Gikomba workshop — idle resource recombination",
    ))

    core.save_graph()

    return {
        "graph_stats": core.graph.stats(),
        "opportunities_detected": len(opps),
        "top_opportunity": opps[0].title if opps else None,
        "geo_features": geo.count(),
    }
