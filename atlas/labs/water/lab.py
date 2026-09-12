"""
Atlas Sanctum — Water Field Lab
Demonstrates the full Phase III loop for a water deployment:
  Sensor → Pipeline → Knowledge Graph → Simulation → Impact Ledger

Can be run standalone as a lab script or imported as a module.
"""
from __future__ import annotations
import logging
from datetime import datetime
from pathlib import Path

from atlas.core.intelligence.core import AtlasCore
from atlas.core.signals.pipeline import SignalPipeline
from atlas.core.gis.index import GeoIndex, GeoFeature
from atlas.schemas.types import Entity, ImpactRecord, ImpactDomain
from atlas.schemas.phase3 import SensorReading, SensorType, GeoPoint

log = logging.getLogger("atlas.labs.water")


def run_water_lab(data_dir: Path, node_id: str = "water-lab-node") -> dict:
    core = AtlasCore(node_id=node_id, data_dir=data_dir)
    pipeline = SignalPipeline(node_id=node_id)
    geo = GeoIndex()

    # Register signal → graph handler
    def _to_graph(sig):
        core.graph.add_entity(Entity(
            id=sig.id, kind="signal",
            label=f"water:{sig.payload.get('sensor_id','')}",
            properties=sig.payload,
        ))

    pipeline.register_handler(_to_graph)

    # Simulate a borehole sensor at a Nairobi community site
    borehole = GeoPoint(latitude=-1.2921, longitude=36.8219)
    geo.add(GeoFeature(
        id="borehole-001", kind="sensor",
        label="Kibera Borehole", location=borehole,
        properties={"depth_m": 45, "community": "Kibera"},
    ))

    # Ingest 3 flow readings
    readings = [
        SensorReading(sensor_id="flow-001", sensor_type=SensorType.WATER_FLOW,
                      node_id=node_id, location=borehole,
                      value=12.4, unit="L/min", quality=0.95),
        SensorReading(sensor_id="flow-001", sensor_type=SensorType.WATER_FLOW,
                      node_id=node_id, location=borehole,
                      value=11.8, unit="L/min", quality=0.92),
        SensorReading(sensor_id="quality-001", sensor_type=SensorType.WATER_QUALITY,
                      node_id=node_id, location=borehole,
                      value=0.3, unit="NTU", quality=0.98,
                      raw={"ph": 7.1, "turbidity_ntu": 0.3}),
    ]
    for r in readings:
        pipeline.ingest(r)

    # Run water demand simulation for the community
    sim = core.simulate("water_demand", {
        "population": 2500,
        "daily_litres_per_person": 20,   # WHO minimum
        "days": 30,
        "loss_factor": 0.12,
    }, label="Kibera 30-day demand")

    # Record impact
    core.impact.record(ImpactRecord(
        domain=ImpactDomain.WATER,
        metric="people_with_water_access",
        value=2500,
        unit="people",
        node_id=node_id,
        notes="Kibera borehole community deployment",
    ))

    core.save_graph()

    return {
        "signals_processed": pipeline.stats()["processed"],
        "graph_stats": core.graph.stats(),
        "simulation": sim.result,
        "geo_features": geo.count(),
        "impact_records": len(core.impact.query(domain=ImpactDomain.WATER)),
    }


if __name__ == "__main__":
    import tempfile
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s")
    with tempfile.TemporaryDirectory() as tmp:
        result = run_water_lab(Path(tmp))
        print("\n=== Water Lab Results ===")
        for k, v in result.items():
            print(f"  {k}: {v}")
