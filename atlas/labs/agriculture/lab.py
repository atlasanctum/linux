"""
Atlas Sanctum — Agriculture Field Lab
Soil moisture + temperature sensors → Pipeline → Crop yield simulation → Impact Ledger
"""
from __future__ import annotations
import logging
from pathlib import Path

from atlas.core.intelligence.core import AtlasCore
from atlas.core.signals.pipeline import SignalPipeline
from atlas.core.gis.index import GeoIndex, GeoFeature
from atlas.schemas.types import Entity, ImpactRecord, ImpactDomain
from atlas.schemas.phase3 import SensorReading, SensorType, GeoPoint

log = logging.getLogger("atlas.labs.agriculture")


def run_agriculture_lab(data_dir: Path, node_id: str = "agri-lab-node") -> dict:
    core = AtlasCore(node_id=node_id, data_dir=data_dir)
    pipeline = SignalPipeline(node_id=node_id)
    geo = GeoIndex()

    def _to_graph(sig):
        core.graph.add_entity(Entity(
            id=sig.id, kind="signal",
            label=f"agri:{sig.payload.get('sensor_id', '')}",
            properties=sig.payload,
        ))

    pipeline.register_handler(_to_graph)

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

    # Register and run a simple crop yield model
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
        "soil_moisture": 0.32,
        "base_yield_kg_ha": 2000,
    }, label="Nakuru maize yield estimate")

    core.impact.record(ImpactRecord(
        domain=ImpactDomain.AGRICULTURE,
        metric="estimated_yield_kg",
        value=sim.result.get("estimated_yield_kg", 0),
        unit="kg",
        node_id=node_id,
        notes="Nakuru maize field — sensor-informed yield estimate",
    ))

    core.save_graph()

    return {
        "signals_processed": pipeline.stats()["processed"],
        "simulation": sim.result,
        "geo_features": geo.count(),
        "impact_records": len(core.impact.query(domain=ImpactDomain.AGRICULTURE)),
    }
