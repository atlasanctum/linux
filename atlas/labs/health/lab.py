"""
Atlas Sanctum — Health Field Lab
Clinic capacity sensors → Pipeline → Patient flow simulation → Impact Ledger
"""
from __future__ import annotations
import logging
from pathlib import Path

from atlas.core.intelligence.core import AtlasCore
from atlas.core.signals.pipeline import SignalPipeline
from atlas.core.gis.index import GeoIndex, GeoFeature
from atlas.schemas.types import Entity, ImpactRecord, ImpactDomain
from atlas.schemas.phase3 import SensorReading, SensorType, GeoPoint

log = logging.getLogger("atlas.labs.health")


def run_health_lab(data_dir: Path, node_id: str = "health-lab-node") -> dict:
    core = AtlasCore(node_id=node_id, data_dir=data_dir)
    pipeline = SignalPipeline(node_id=node_id)
    geo = GeoIndex()

    def _to_graph(sig):
        core.graph.add_entity(Entity(
            id=sig.id, kind="signal",
            label=f"health:{sig.payload.get('sensor_id', '')}",
            properties=sig.payload,
        ))

    pipeline.register_handler(_to_graph)

    clinic = GeoPoint(latitude=-1.2864, longitude=36.8172)
    geo.add(GeoFeature(
        id="clinic-001", kind="facility",
        label="Mathare Community Clinic", location=clinic,
        properties={"beds": 20, "staff": 8, "catchment_population": 15000},
    ))

    # Custom sensor readings for clinic occupancy
    readings = [
        SensorReading(sensor_id="occupancy-001", sensor_type=SensorType.CUSTOM,
                      node_id=node_id, location=clinic,
                      value=14.0, unit="patients", quality=0.99,
                      raw={"capacity": 20, "occupancy_rate": 0.70}),
        SensorReading(sensor_id="wait-001", sensor_type=SensorType.CUSTOM,
                      node_id=node_id, location=clinic,
                      value=47.0, unit="minutes", quality=0.95,
                      raw={"target_wait_min": 30}),
    ]
    for r in readings:
        pipeline.ingest(r)

    def patient_flow_model(params: dict) -> dict:
        daily_patients = float(params.get("daily_patients", 80))
        staff = int(params.get("staff", 8))
        beds = int(params.get("beds", 20))
        days = int(params.get("days", 30))
        capacity_per_staff = 12
        max_daily = staff * capacity_per_staff
        overflow_days = sum(1 for _ in range(days) if daily_patients > max_daily)
        served = min(daily_patients, max_daily) * days
        return {
            "daily_capacity": max_daily,
            "overflow_days": overflow_days,
            "total_patients_served": round(served),
            "utilisation_rate": round(daily_patients / max_daily, 3),
        }

    core.simulation.register("patient_flow", patient_flow_model)
    sim = core.simulate("patient_flow", {
        "daily_patients": 95,
        "staff": 8,
        "beds": 20,
        "days": 30,
    }, label="Mathare clinic 30-day flow")

    core.impact.record(ImpactRecord(
        domain=ImpactDomain.HEALTH,
        metric="patients_served",
        value=sim.result.get("total_patients_served", 0),
        unit="patients",
        node_id=node_id,
        notes="Mathare Community Clinic — 30-day projection",
    ))

    core.save_graph()

    return {
        "signals_processed": pipeline.stats()["processed"],
        "simulation": sim.result,
        "geo_features": geo.count(),
        "impact_records": len(core.impact.query(domain=ImpactDomain.HEALTH)),
    }
