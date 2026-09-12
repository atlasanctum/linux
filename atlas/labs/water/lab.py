"""
Atlas Sanctum — Water Field Lab  (Phase IV complete)
Full loop: Sensor → Pipeline → Knowledge Graph → Digital Twin →
           Simulation → Invention → Prototype → Impact Ledger
"""
from __future__ import annotations
import logging
from pathlib import Path

from atlas.core.intelligence.core import AtlasCore
from atlas.core.signals.pipeline import SignalPipeline
from atlas.core.gis.index import GeoIndex, GeoFeature
from atlas.schemas.types import Entity, ImpactRecord, ImpactDomain, Signal, SignalSource
from atlas.schemas.phase3 import SensorReading, SensorType, GeoPoint
from atlas.schemas.phase4 import PrototypeStatus

log = logging.getLogger("atlas.labs.water")


def run_water_lab(data_dir: Path, node_id: str = "water-lab-node") -> dict:
    core = AtlasCore(node_id=node_id, data_dir=data_dir)
    pipeline = SignalPipeline(node_id=node_id)
    geo = GeoIndex()

    # --- Digital twin for the borehole pump ---
    twin = core.twins.create(
        name="Kibera Borehole Pump",
        asset_id="borehole-001",
        model_type="water_pump",
        initial_state={"flow_rate": 0.0, "pressure": 2.0},
    )

    def _to_graph_and_twin(sig: Signal) -> None:
        core.graph.add_entity(Entity(
            id=sig.id, kind="signal",
            label=f"water:{sig.payload.get('sensor_id', '')}",
            properties=sig.payload,
        ))
        core.twins.sync(twin.id, sig)

    pipeline.register_handler(_to_graph_and_twin)

    borehole = GeoPoint(latitude=-1.2921, longitude=36.8219)
    geo.add(GeoFeature(
        id="borehole-001", kind="sensor",
        label="Kibera Borehole", location=borehole,
        properties={"depth_m": 45, "community": "Kibera"},
    ))

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

    # --- Simulation ---
    sim = core.simulate("water_demand", {
        "population": 2500,
        "daily_litres_per_person": 20,
        "days": 30,
        "loss_factor": 0.12,
    }, label="Kibera 30-day demand")

    # --- Twin experiment: what if we increase pump pressure? ---
    def pressure_experiment(t, params):
        new_pressure = params.get("pressure", t.state.get("pressure", 2.0))
        flow_gain = (new_pressure - t.state.get("pressure", 2.0)) * 1.5
        return {
            "projected_flow_rate": round(t.state.get("flow_rate", 0) + flow_gain, 2),
            "pressure_applied": new_pressure,
        }

    exp = core.twins.run_experiment(
        twin.id,
        hypothesis="Increase pump pressure to improve flow rate",
        parameters={"pressure": 3.5},
        experiment_fn=pressure_experiment,
    )

    # --- Invention proposal ---
    core.graph.add_entity(Entity(
        kind="unused_resource", label="Idle Pump Capacity",
        properties={"domain": "water", "availability": 0.6},
    ))
    proposals = core.invent(top_n=3)

    # --- Prototype lifecycle ---
    prototype = None
    if proposals:
        prototype = core.prototypes.start(proposals[0])
        core.prototypes.advance(prototype.id, notes="Community needs assessment complete")
        core.prototypes.advance(prototype.id, notes="Pump upgrade design finalised")

    # --- Impact ---
    core.impact.record(ImpactRecord(
        domain=ImpactDomain.WATER,
        metric="people_with_water_access",
        value=2500, unit="people",
        node_id=node_id,
        notes="Kibera borehole community deployment",
    ))

    core.save_graph()

    return {
        "signals_processed": pipeline.stats()["processed"],
        "graph_stats": core.graph.stats(),
        "simulation": sim.result,
        "twin_state": core.twins.get(twin.id).state,
        "twin_history_snapshots": len(core.twins.history(twin.id)),
        "experiment_result": exp.result,
        "proposals_generated": len(proposals),
        "prototype_stage": prototype.status.value if prototype else None,
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
