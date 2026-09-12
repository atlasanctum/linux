"""
Atlas Sanctum — Cities Field Lab
GPS + infrastructure sensors → Pipeline → Urban capacity simulation → Impact Ledger
"""
from __future__ import annotations
import logging
from pathlib import Path

from atlas.core.intelligence.core import AtlasCore
from atlas.core.signals.pipeline import SignalPipeline
from atlas.core.gis.index import GeoIndex, GeoFeature
from atlas.schemas.types import Entity, ImpactRecord, ImpactDomain
from atlas.schemas.phase3 import SensorReading, SensorType, GeoPoint

log = logging.getLogger("atlas.labs.cities")


def run_cities_lab(data_dir: Path, node_id: str = "cities-lab-node") -> dict:
    core = AtlasCore(node_id=node_id, data_dir=data_dir)
    pipeline = SignalPipeline(node_id=node_id)
    geo = GeoIndex()

    def _to_graph(sig):
        core.graph.add_entity(Entity(
            id=sig.id, kind="signal",
            label=f"city:{sig.payload.get('sensor_id', '')}",
            properties=sig.payload,
        ))

    pipeline.register_handler(_to_graph)

    # Key Nairobi infrastructure points
    cbd = GeoPoint(latitude=-1.2833, longitude=36.8167)
    westlands = GeoPoint(latitude=-1.2667, longitude=36.8000)

    for feat in [
        GeoFeature(id="junction-001", kind="infrastructure",
                   label="CBD Junction", location=cbd,
                   properties={"type": "road_junction", "lanes": 4}),
        GeoFeature(id="junction-002", kind="infrastructure",
                   label="Westlands Roundabout", location=westlands,
                   properties={"type": "roundabout", "lanes": 3}),
    ]:
        geo.add(feat)

    readings = [
        SensorReading(sensor_id="traffic-001", sensor_type=SensorType.GPS,
                      node_id=node_id, location=cbd,
                      value=1240.0, unit="vehicles/hour", quality=0.93),
        SensorReading(sensor_id="traffic-002", sensor_type=SensorType.GPS,
                      node_id=node_id, location=westlands,
                      value=870.0, unit="vehicles/hour", quality=0.91),
    ]
    for r in readings:
        pipeline.ingest(r)

    def urban_capacity_model(params: dict) -> dict:
        population = float(params.get("population", 100000))
        infrastructure_score = float(params.get("infrastructure_score", 0.6))
        daily_trips = population * 2.1
        capacity = infrastructure_score * population * 2.5
        congestion_index = min(1.0, daily_trips / capacity)
        return {
            "daily_trips": round(daily_trips),
            "system_capacity": round(capacity),
            "congestion_index": round(congestion_index, 3),
            "needs_investment": congestion_index > 0.8,
        }

    core.simulation.register("urban_capacity", urban_capacity_model)
    sim = core.simulate("urban_capacity", {
        "population": 500000,
        "infrastructure_score": 0.55,
    }, label="Nairobi CBD capacity assessment")

    core.impact.record(ImpactRecord(
        domain=ImpactDomain.CITIES,
        metric="congestion_index",
        value=sim.result.get("congestion_index", 0),
        unit="index",
        node_id=node_id,
        notes="Nairobi CBD — urban capacity baseline",
    ))

    core.save_graph()

    return {
        "signals_processed": pipeline.stats()["processed"],
        "simulation": sim.result,
        "geo_features": geo.count(),
        "impact_records": len(core.impact.query(domain=ImpactDomain.CITIES)),
    }
