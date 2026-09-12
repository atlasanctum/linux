"""
Atlas Sanctum — Node REST API  (Phase III)
FastAPI application mounted on the AtlasNode.

Endpoints:
  GET  /                        node status
  GET  /health                  liveness
  POST /signals                 ingest a sensor reading
  GET  /opportunities           list ranked opportunities
  POST /simulate/{model}        run a simulation
  GET  /impact                  impact ledger summary
  GET  /gis/features            GeoJSON feature collection
  POST /gis/features            add a geo feature
  GET  /gis/radius              features within radius of a point
"""
from __future__ import annotations
from datetime import datetime
from typing import Any

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel
    _FASTAPI = True
except ImportError:
    _FASTAPI = False

from atlas.schemas.phase3 import SensorReading, SensorType, GeoPoint, GeoFeature
from atlas.core.gis.index import GeoIndex, haversine_km


def create_app(core, signal_pipeline, geo_index: GeoIndex) -> Any:
    if not _FASTAPI:
        raise RuntimeError("FastAPI is required for the node API: pip install fastapi uvicorn")

    app = FastAPI(title="Atlas Node API", version="3.0.0")

    # ------------------------------------------------------------------ models

    class SignalIn(BaseModel):
        sensor_id: str
        sensor_type: str = "custom"
        value: float
        unit: str = ""
        quality: float = 1.0
        latitude: float | None = None
        longitude: float | None = None
        raw: dict[str, Any] = {}

    class SimulateIn(BaseModel):
        parameters: dict[str, Any]
        label: str = ""

    class GeoFeatureIn(BaseModel):
        id: str
        kind: str = "entity"
        label: str = ""
        latitude: float
        longitude: float
        properties: dict[str, Any] = {}

    # ------------------------------------------------------------------ routes

    @app.get("/")
    def node_status():
        return {
            "node_id": core.node_id,
            "status": "running",
            "ts": datetime.utcnow().isoformat() + "Z",
            "agents": core.agents.agents(),
            "graph_stats": core.graph.stats(),
        }

    @app.get("/health")
    def health():
        return {"ok": True}

    @app.post("/signals", status_code=201)
    def ingest_signal(body: SignalIn):
        location = None
        if body.latitude is not None and body.longitude is not None:
            location = GeoPoint(latitude=body.latitude, longitude=body.longitude)
        reading = SensorReading(
            sensor_id=body.sensor_id,
            sensor_type=SensorType(body.sensor_type),
            node_id=core.node_id,
            location=location,
            value=body.value,
            unit=body.unit,
            quality=body.quality,
            raw=body.raw,
        )
        signal = signal_pipeline.ingest(reading)
        if signal is None:
            raise HTTPException(status_code=422, detail="Signal failed validation")
        return {"signal_id": signal.id, "domain": signal.domain.value}

    @app.get("/opportunities")
    def list_opportunities(top_n: int = 10):
        opps = core.scan_opportunities(top_n=top_n)
        return [
            {"id": o.id, "title": o.title, "domain": o.domain.value,
             "score": round(o.score, 3), "status": o.status.value}
            for o in opps
        ]

    @app.post("/simulate/{model}")
    def run_simulation(model: str, body: SimulateIn):
        run = core.simulate(model, body.parameters, label=body.label)
        return {
            "run_id": run.id,
            "model": run.model,
            "status": run.status.value,
            "result": run.result,
        }

    @app.get("/impact")
    def impact_summary(domain: str | None = None):
        from atlas.schemas.types import ImpactDomain
        d = ImpactDomain(domain) if domain else None
        records = core.impact.query(domain=d)
        return {
            "total": len(records),
            "summary": core.impact.summary(),
        }

    @app.get("/gis/features")
    def gis_features():
        return geo_index.to_geojson_collection()

    @app.post("/gis/features", status_code=201)
    def add_gis_feature(body: GeoFeatureIn):
        feature = GeoFeature(
            id=body.id,
            kind=body.kind,
            label=body.label,
            location=GeoPoint(latitude=body.latitude, longitude=body.longitude),
            properties=body.properties,
        )
        geo_index.add(feature)
        return {"id": feature.id}

    @app.get("/gis/radius")
    def gis_radius(lat: float, lon: float, radius_km: float = 10.0):
        centre = GeoPoint(latitude=lat, longitude=lon)
        features = list(geo_index.within_radius(centre, radius_km))
        return {
            "type": "FeatureCollection",
            "features": [f.to_geojson() for f in features],
        }

    return app
