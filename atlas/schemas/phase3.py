"""
Atlas Sanctum — Phase III Schema Extensions
SensorReading, GeoPoint, SyncEnvelope, SyncStatus
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
import uuid


def _uid() -> str:
    return str(uuid.uuid4())


class SyncStatus(str, Enum):
    QUEUED = "queued"
    SENT = "sent"
    ACKNOWLEDGED = "acknowledged"
    FAILED = "failed"


class SensorType(str, Enum):
    WATER_FLOW = "water_flow"
    WATER_QUALITY = "water_quality"
    SOIL_MOISTURE = "soil_moisture"
    AIR_QUALITY = "air_quality"
    TEMPERATURE = "temperature"
    HUMIDITY = "humidity"
    POWER_METER = "power_meter"
    GPS = "gps"
    CAMERA = "camera"
    CUSTOM = "custom"


@dataclass
class GeoPoint:
    latitude: float = 0.0
    longitude: float = 0.0
    altitude_m: float | None = None
    accuracy_m: float | None = None

    def to_geojson(self) -> dict:
        coords = [self.longitude, self.latitude]
        if self.altitude_m is not None:
            coords.append(self.altitude_m)
        return {"type": "Point", "coordinates": coords}

    @staticmethod
    def from_geojson(data: dict) -> "GeoPoint":
        coords = data["coordinates"]
        return GeoPoint(
            latitude=coords[1],
            longitude=coords[0],
            altitude_m=coords[2] if len(coords) > 2 else None,
        )


@dataclass
class SensorReading:
    id: str = field(default_factory=_uid)
    sensor_id: str = ""
    sensor_type: SensorType = SensorType.CUSTOM
    node_id: str = ""
    location: GeoPoint | None = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    value: float = 0.0
    unit: str = ""
    quality: float = 1.0          # 0–1 data quality confidence
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class SyncEnvelope:
    """Wraps a payload for offline-resilient node-to-node sync."""
    id: str = field(default_factory=_uid)
    origin_node_id: str = ""
    target_node_id: str = ""      # empty = broadcast to peers
    payload_type: str = ""        # e.g. "signal", "opportunity", "impact_record"
    payload: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    status: SyncStatus = SyncStatus.QUEUED
    attempts: int = 0
    signature: str = ""           # Ed25519 hex signature of payload
