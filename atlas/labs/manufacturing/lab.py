"""
Atlas Sanctum — Manufacturing Field Lab  (Phase IV complete)
Idle machines + waste → Opportunity Graph → Workshop Twin →
Robotics inspection → Invention → Prototype → Impact Ledger
"""
from __future__ import annotations
import logging
from pathlib import Path

from atlas.core.intelligence.core import AtlasCore
from atlas.core.gis.index import GeoIndex, GeoFeature
from atlas.core.adapters.robotics import SimulationRoboticsAdapter
from atlas.schemas.types import Entity, Relation, ImpactRecord, ImpactDomain, Signal, SignalSource
from atlas.schemas.phase3 import GeoPoint
from atlas.schemas.phase4 import RoboticsTask

log = logging.getLogger("atlas.labs.manufacturing")


def run_manufacturing_lab(data_dir: Path, node_id: str = "mfg-lab-node") -> dict:
    core = AtlasCore(node_id=node_id, data_dir=data_dir)
    geo = GeoIndex()
    robotics = SimulationRoboticsAdapter(node_id=node_id)

    workshop = GeoPoint(latitude=-1.3167, longitude=36.8833)
    geo.add(GeoFeature(
        id="workshop-001", kind="facility",
        label="Gikomba Workshop", location=workshop,
        properties={"type": "metal_fabrication"},
    ))

    # --- Digital twin for the workshop ---
    twin = core.twins.create(
        name="Gikomba Workshop",
        asset_id="workshop-001",
        model_type="workshop",
        initial_state={"utilisation": 0.25, "idle": True, "machines": 4},
    )

    # Populate knowledge graph
    entities = [
        Entity(id="m1", kind="unused_resource", label="Idle Metal Lathe",
               properties={"domain": "manufacturing", "availability": 0.8}),
        Entity(id="m2", kind="unused_resource", label="Scrap Steel Stock",
               properties={"domain": "manufacturing", "availability": 0.9}),
        Entity(id="s1", kind="skill", label="Welding Expertise",
               properties={"domain": "manufacturing", "workers": 3}),
        Entity(id="n1", kind="need", label="Affordable Roofing Brackets",
               properties={"domain": "manufacturing", "urgency": 0.85}),
        Entity(id="n2", kind="need", label="Water Tank Fittings",
               properties={"domain": "manufacturing", "urgency": 0.75}),
    ]
    for e in entities:
        core.graph.add_entity(e)

    core.graph.add_relation(Relation(source_id="m1", target_id="n1", kind="can_produce"))
    core.graph.add_relation(Relation(source_id="m2", target_id="n1", kind="material_for"))
    core.graph.add_relation(Relation(source_id="s1", target_id="n1", kind="skill_for"))
    core.graph.add_relation(Relation(source_id="m1", target_id="n2", kind="can_produce"))

    # --- Robotics: inspect the workshop ---
    task = RoboticsTask(
        robot_id="inspection-drone-01",
        task_type="inspect",
        parameters={"target": "workshop-001", "focus": "machine_condition"},
        node_id=node_id,
    )
    completed_task = robotics.dispatch(task)

    # Feed robotics readings back into the twin via a synthetic signal
    for reading in robotics.readings(completed_task):
        sig = Signal(
            source=SignalSource.SENSOR,
            domain=ImpactDomain.MANUFACTURING,
            node_id=node_id,
            payload={
                "sensor_id": reading.sensor_id,
                "value": reading.value,
                "quality": reading.quality,
            },
        )
        core.twins.sync(twin.id, sig)

    # --- Opportunity scan + invention ---
    opps = core.scan_opportunities(top_n=5)
    proposals = core.invent(top_n=3)

    # --- Prototype lifecycle ---
    prototype = None
    if proposals:
        prototype = core.prototypes.start(proposals[0])
        core.prototypes.advance(prototype.id, notes="Bill of materials drafted")
        core.prototypes.advance(prototype.id, notes="First bracket prototype fabricated")
        core.prototypes.advance(prototype.id, notes="Load testing in progress")

    core.impact.record(ImpactRecord(
        domain=ImpactDomain.MANUFACTURING,
        metric="opportunities_detected",
        value=len(opps), unit="opportunities",
        node_id=node_id,
        notes="Gikomba workshop — idle resource recombination",
    ))

    core.save_graph()

    return {
        "graph_stats": core.graph.stats(),
        "opportunities_detected": len(opps),
        "twin_state": core.twins.get(twin.id).state,
        "robotics_task_status": completed_task.status.value,
        "proposals_generated": len(proposals),
        "prototype_stage": prototype.status.value if prototype else None,
        "geo_features": geo.count(),
    }


if __name__ == "__main__":
    import tempfile
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s")
    with tempfile.TemporaryDirectory() as tmp:
        result = run_manufacturing_lab(Path(tmp))
        print("\n=== Manufacturing Lab Results ===")
        for k, v in result.items():
            print(f"  {k}: {v}")
