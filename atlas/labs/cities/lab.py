"""
Atlas Sanctum — Cities Field Lab  (Phase IV complete)
Traffic sensors → Pipeline → Junction Twin →
Robotics survey → Simulation → Invention → Prototype → Impact Ledger
"""
from __future__ import annotations
import logging
from pathlib import Path

from atlas.core.intelligence.core import AtlasCore
from atlas.core.signals.pipeline import SignalPipeline
from atlas.core.gis.index import GeoIndex, GeoFeature
from atlas.core.adapters.robotics import SimulationRoboticsAdapter
from atlas.schemas.types import Entity, ImpactRecord, ImpactDomain, Signal, SignalSource
from atlas.schemas.phase3 import SensorReading, SensorType, GeoPoint
from atlas.schemas.phase4 import RoboticsTask

log = logging.getLogger("atlas.labs.cities")


def run_cities_lab(data_dir: Path, node_id: str = "cities-lab-node") -> dict:
    core = AtlasCore(node_id=node_id, data_dir=data_dir)
    pipeline = SignalPipeline(node_id=node_id)
    geo = GeoIndex()
    robotics = SimulationRoboticsAdapter(node_id=node_id)

    cbd = GeoPoint(latitude=-1.2833, longitude=36.8167)
    westlands = GeoPoint(latitude=-1.2667, longitude=36.8000)

    twin = core.twins.create(
        name="Nairobi CBD Junction",
        asset_id="junction-001",
        model_type="traffic_junction",
        initial_state={"vehicles_per_hour": 0, "capacity_vph": 1500,
                       "congestion_ratio": 0.0, "congested": False},
    )

    def _to_graph_and_twin(sig: Signal) -> None:
        core.graph.add_entity(Entity(
            id=sig.id, kind="signal",
            label=f"city:{sig.payload.get('sensor_id', '')}",
            properties=sig.payload,
        ))
        core.twins.sync(twin.id, sig)

    pipeline.register_handler(_to_graph_and_twin)

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

    # --- Robotics: aerial survey of CBD junction ---
    task = RoboticsTask(
        robot_id="survey-drone-01",
        task_type="survey",
        parameters={"area_m2": 5000, "target": "junction-001"},
        node_id=node_id,
    )
    completed_task = robotics.dispatch(task)

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

    def lane_expansion_experiment(t, params):
        extra_lanes = params.get("extra_lanes", 2)
        current_capacity = t.state.get("capacity_vph", 1500)
        new_capacity = current_capacity + extra_lanes * 300
        current_vph = t.state.get("vehicles_per_hour", 1240)
        return {
            "new_capacity_vph": new_capacity,
            "new_congestion_ratio": round(current_vph / new_capacity, 3),
            "congestion_eliminated": current_vph <= new_capacity * 0.85,
        }

    exp = core.twins.run_experiment(
        twin.id,
        hypothesis="Add 2 lanes to CBD junction to reduce congestion",
        parameters={"extra_lanes": 2},
        experiment_fn=lane_expansion_experiment,
    )

    core.graph.add_entity(Entity(
        kind="unused_resource", label="Underutilised Road Capacity",
        properties={"domain": "cities", "availability": 0.4},
    ))
    proposals = core.invent(top_n=3)

    prototype = None
    if proposals:
        prototype = core.prototypes.start(proposals[0])
        core.prototypes.advance(prototype.id, notes="Traffic flow study commissioned")

    core.impact.record(ImpactRecord(
        domain=ImpactDomain.CITIES,
        metric="congestion_index",
        value=sim.result.get("congestion_index", 0),
        unit="index", node_id=node_id,
        notes="Nairobi CBD — urban capacity baseline",
    ))

    core.save_graph()

    return {
        "signals_processed": pipeline.stats()["processed"],
        "simulation": sim.result,
        "twin_state": core.twins.get(twin.id).state,
        "robotics_task_status": completed_task.status.value,
        "experiment_result": exp.result,
        "proposals_generated": len(proposals),
        "prototype_stage": prototype.status.value if prototype else None,
        "geo_features": geo.count(),
        "impact_records": len(core.impact.query(domain=ImpactDomain.CITIES)),
    }


if __name__ == "__main__":
    import tempfile
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s")
    with tempfile.TemporaryDirectory() as tmp:
        result = run_cities_lab(Path(tmp))
        print("\n=== Cities Lab Results ===")
        for k, v in result.items():
            print(f"  {k}: {v}")
