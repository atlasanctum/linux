"""
Atlas Sanctum — Agriculture Field Lab  (Phase IV complete)
Soil/temp/humidity → Pipeline → Crop Field Twin →
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

log = logging.getLogger("atlas.labs.agriculture")


def run_agriculture_lab(data_dir: Path, node_id: str = "agri-lab-node") -> dict:
    core = AtlasCore(node_id=node_id, data_dir=data_dir)
    pipeline = SignalPipeline(node_id=node_id)
    geo = GeoIndex()

    twin = core.twins.create(
        name="Nakuru Maize Field",
        asset_id="field-001",
        model_type="crop_field",
        initial_state={"soil_moisture": 0.3, "temperature_c": 22.0,
                       "humidity_pct": 65.0, "water_stress_index": 0.14},
    )

    def _to_graph_and_twin(sig: Signal) -> None:
        core.graph.add_entity(Entity(
            id=sig.id, kind="signal",
            label=f"agri:{sig.payload.get('sensor_id', '')}",
            properties=sig.payload,
        ))
        core.twins.sync(twin.id, sig)

    pipeline.register_handler(_to_graph_and_twin)

    field = GeoPoint(latitude=-0.4167, longitude=36.9500)
    geo.add(GeoFeature(
        id="field-001", kind="sensor",
        label="Nakuru Maize Field", location=field,
        properties={"crop": "maize", "area_ha": 2.5},
    ))

    readings = [
        SensorReading(sensor_id="soil-001", sensor_type=SensorType.SOIL_MOISTURE,
                      node_id=node_id, location=field,
                      value=0.32, unit="m3/m3", quality=0.91),
        SensorReading(sensor_id="temp-001", sensor_type=SensorType.TEMPERATURE,
                      node_id=node_id, location=field,
                      value=24.5, unit="°C", quality=0.97),
        SensorReading(sensor_id="humidity-001", sensor_type=SensorType.HUMIDITY,
                      node_id=node_id, location=field,
                      value=68.0, unit="%", quality=0.95),
    ]
    for r in readings:
        pipeline.ingest(r)

    def crop_yield_model(params: dict) -> dict:
        area_ha = float(params.get("area_ha", 1.0))
        soil_moisture = float(params.get("soil_moisture", 0.3))
        base_yield_kg_ha = float(params.get("base_yield_kg_ha", 2000))
        moisture_factor = min(1.0, soil_moisture / 0.35)
        estimated_yield = area_ha * base_yield_kg_ha * moisture_factor
        return {
            "area_ha": area_ha,
            "estimated_yield_kg": round(estimated_yield),
            "moisture_factor": round(moisture_factor, 3),
            "yield_per_ha": round(estimated_yield / area_ha),
        }

    core.simulation.register("crop_yield", crop_yield_model)
    sim = core.simulate("crop_yield", {
        "area_ha": 2.5,
        "soil_moisture": core.twins.get(twin.id).state.get("soil_moisture", 0.32),
        "base_yield_kg_ha": 2000,
    }, label="Nakuru maize yield estimate")

    def irrigation_experiment(t, params):
        target_moisture = params.get("target_moisture", 0.38)
        current = t.state.get("soil_moisture", 0.3)
        water_needed_mm = max(0, (target_moisture - current) * 1000 * params.get("depth_m", 0.3))
        new_yield_factor = min(1.0, target_moisture / 0.35)
        return {
            "water_needed_mm": round(water_needed_mm, 1),
            "projected_yield_factor": round(new_yield_factor, 3),
            "yield_improvement_pct": round((new_yield_factor - current / 0.35) * 100, 1),
        }

    exp = core.twins.run_experiment(
        twin.id,
        hypothesis="Targeted irrigation to reach optimal soil moisture",
        parameters={"target_moisture": 0.38, "depth_m": 0.3},
        experiment_fn=irrigation_experiment,
    )

    core.graph.add_entity(Entity(
        kind="unused_resource", label="Underutilised Farmland",
        properties={"domain": "agriculture", "availability": 0.65},
    ))
    proposals = core.invent(top_n=3)

    prototype = None
    if proposals:
        prototype = core.prototypes.start(proposals[0])
        core.prototypes.advance(prototype.id, notes="Drip irrigation design scoped")
        core.prototypes.advance(prototype.id, notes="Materials sourced locally")

    core.impact.record(ImpactRecord(
        domain=ImpactDomain.AGRICULTURE,
        metric="estimated_yield_kg",
        value=sim.result.get("estimated_yield_kg", 0),
        unit="kg", node_id=node_id,
        notes="Nakuru maize field — sensor-informed yield estimate",
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
        "impact_records": len(core.impact.query(domain=ImpactDomain.AGRICULTURE)),
    }


if __name__ == "__main__":
    import tempfile
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s")
    with tempfile.TemporaryDirectory() as tmp:
        result = run_agriculture_lab(Path(tmp))
        print("\n=== Agriculture Lab Results ===")
        for k, v in result.items():
            print(f"  {k}: {v}")
