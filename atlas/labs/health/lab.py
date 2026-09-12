"""
Atlas Sanctum — Health Field Lab  (Phase IV complete)
Clinic sensors → Pipeline → Clinic Twin →
Simulation → Invention → Prototype → Impact Ledger
"""
from __future__ import annotations
import logging
from pathlib import Path

from atlas.core.intelligence.core import AtlasCore
from atlas.core.signals.pipeline import SignalPipeline
from atlas.core.gis.index import GeoIndex, GeoFeature
from atlas.schemas.types import Entity, ImpactRecord, ImpactDomain, Signal
from atlas.schemas.phase3 import SensorReading, SensorType, GeoPoint

log = logging.getLogger("atlas.labs.health")


def run_health_lab(data_dir: Path, node_id: str = "health-lab-node") -> dict:
    core = AtlasCore(node_id=node_id, data_dir=data_dir)
    pipeline = SignalPipeline(node_id=node_id)
    geo = GeoIndex()

    twin = core.twins.create(
        name="Mathare Community Clinic",
        asset_id="clinic-001",
        model_type="clinic",
        initial_state={"capacity": 20, "current_patients": 0,
                       "occupancy_rate": 0.0, "avg_wait_min": 0.0},
    )

    def _to_graph_and_twin(sig: Signal) -> None:
        core.graph.add_entity(Entity(
            id=sig.id, kind="signal",
            label=f"health:{sig.payload.get('sensor_id', '')}",
            properties=sig.payload,
        ))
        core.twins.sync(twin.id, sig)

    pipeline.register_handler(_to_graph_and_twin)

    clinic = GeoPoint(latitude=-1.2864, longitude=36.8172)
    geo.add(GeoFeature(
        id="clinic-001", kind="facility",
        label="Mathare Community Clinic", location=clinic,
        properties={"beds": 20, "staff": 8, "catchment_population": 15000},
    ))

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
        days = int(params.get("days", 30))
        max_daily = staff * 12
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
        "daily_patients": 95, "staff": 8, "days": 30,
    }, label="Mathare clinic 30-day flow")

    def staffing_experiment(t, params):
        extra_staff = params.get("extra_staff", 2)
        new_capacity = (t.state.get("capacity", 20) + extra_staff) * 12
        current_patients = params.get("daily_patients", 95)
        return {
            "new_daily_capacity": new_capacity,
            "overflow_eliminated": current_patients <= new_capacity,
            "wait_reduction_pct": round(extra_staff / 8 * 100, 1),
        }

    exp = core.twins.run_experiment(
        twin.id,
        hypothesis="Add 2 staff to eliminate overflow and reduce wait times",
        parameters={"extra_staff": 2, "daily_patients": 95},
        experiment_fn=staffing_experiment,
    )

    core.graph.add_entity(Entity(
        kind="unused_resource", label="Underutilised Clinic Hours",
        properties={"domain": "health", "availability": 0.55},
    ))
    proposals = core.invent(top_n=3)

    prototype = None
    if proposals:
        prototype = core.prototypes.start(proposals[0])
        core.prototypes.advance(prototype.id, notes="Community health worker programme scoped")

    core.impact.record(ImpactRecord(
        domain=ImpactDomain.HEALTH,
        metric="patients_served",
        value=sim.result.get("total_patients_served", 0),
        unit="patients", node_id=node_id,
        notes="Mathare Community Clinic — 30-day projection",
    ))

    core.save_graph()

    return {
        "signals_processed": pipeline.stats()["processed"],
        "simulation": sim.result,
        "twin_state": core.twins.get(twin.id).state,
        "experiment_result": exp.result,
        "proposals_generated": len(proposals),
        "prototype_stage": prototype.status.value if prototype else None,
        "geo_features": geo.count(),
        "impact_records": len(core.impact.query(domain=ImpactDomain.HEALTH)),
    }


if __name__ == "__main__":
    import tempfile
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s")
    with tempfile.TemporaryDirectory() as tmp:
        result = run_health_lab(Path(tmp))
        print("\n=== Health Lab Results ===")
        for k, v in result.items():
            print(f"  {k}: {v}")
