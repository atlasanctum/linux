"""
Atlas Sanctum — Energy Field Lab  (Phase IV complete)
Solar + battery: Sensor → Pipeline → Digital Twin →
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

log = logging.getLogger("atlas.labs.energy")


def run_energy_lab(data_dir: Path, node_id: str = "energy-lab-node") -> dict:
    core = AtlasCore(node_id=node_id, data_dir=data_dir)
    pipeline = SignalPipeline(node_id=node_id)
    geo = GeoIndex()

    twin = core.twins.create(
        name="Kawangware Solar Array",
        asset_id="solar-array-001",
        model_type="solar_array",
        initial_state={"output_kwh": 0.0, "battery_kwh": 40.0},
    )

    def _to_graph_and_twin(sig: Signal) -> None:
        core.graph.add_entity(Entity(
            id=sig.id, kind="signal",
            label=f"energy:{sig.payload.get('sensor_id', '')}",
            properties=sig.payload,
        ))
        core.twins.sync(twin.id, sig)

    pipeline.register_handler(_to_graph_and_twin)

    site = GeoPoint(latitude=-1.3032, longitude=36.7073)
    geo.add(GeoFeature(
        id="solar-array-001", kind="sensor",
        label="Kawangware Solar Array", location=site,
        properties={"capacity_kw": 15, "battery_kwh": 40},
    ))

    readings = [
        SensorReading(sensor_id="gen-001", sensor_type=SensorType.POWER_METER,
                      node_id=node_id, location=site,
                      value=14.2, unit="kWh/day", quality=0.97),
        SensorReading(sensor_id="demand-001", sensor_type=SensorType.POWER_METER,
                      node_id=node_id, location=site,
                      value=11.5, unit="kWh/day", quality=0.95),
    ]
    for r in readings:
        pipeline.ingest(r)

    sim = core.simulate("energy_balance", {
        "generation_kwh_day": 14.2,
        "storage_kwh": 40,
        "demand_kwh_day": 11.5,
        "days": 30,
    }, label="Kawangware 30-day balance")

    def battery_expansion_experiment(t, params):
        extra_kwh = params.get("extra_storage_kwh", 20)
        new_storage = t.state.get("battery_kwh", 40) + extra_kwh
        deficit_coverage = new_storage / max(1, params.get("daily_deficit_kwh", 5))
        return {
            "new_storage_kwh": new_storage,
            "deficit_days_covered": round(deficit_coverage, 1),
        }

    exp = core.twins.run_experiment(
        twin.id,
        hypothesis="Add 20 kWh battery storage to eliminate deficit days",
        parameters={"extra_storage_kwh": 20, "daily_deficit_kwh": 5},
        experiment_fn=battery_expansion_experiment,
    )

    core.graph.add_entity(Entity(
        kind="unused_resource", label="Surplus Solar Generation",
        properties={"domain": "energy", "availability": 0.7},
    ))
    proposals = core.invent(top_n=3)

    prototype = None
    if proposals:
        prototype = core.prototypes.start(proposals[0])
        core.prototypes.advance(prototype.id, notes="Battery supplier identified")

    core.impact.record(ImpactRecord(
        domain=ImpactDomain.ENERGY,
        metric="households_with_reliable_power",
        value=85, unit="households",
        node_id=node_id,
        notes="Kawangware solar microgrid",
    ))

    core.save_graph()

    return {
        "signals_processed": pipeline.stats()["processed"],
        "simulation": sim.result,
        "twin_state": core.twins.get(twin.id).state,
        "experiment_result": exp.result,
        "proposals_generated": len(proposals),
        "prototype_stage": prototype.status.value if prototype else None,
        "impact_records": len(core.impact.query(domain=ImpactDomain.ENERGY)),
    }


if __name__ == "__main__":
    import tempfile
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s")
    with tempfile.TemporaryDirectory() as tmp:
        result = run_energy_lab(Path(tmp))
        print("\n=== Energy Lab Results ===")
        for k, v in result.items():
            print(f"  {k}: {v}")
