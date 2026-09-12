"""
Atlas Sanctum — Signal Ingestion Pipeline
Receives SensorReadings, validates them, converts to Signal schema,
and routes to registered handlers (knowledge graph, impact ledger, etc.).
"""
from __future__ import annotations
import logging
from datetime import datetime
from typing import Callable

from atlas.schemas.types import Signal, SignalSource, ImpactDomain
from atlas.schemas.phase3 import SensorReading, SensorType

log = logging.getLogger("atlas.core.signals")

SignalHandler = Callable[[Signal], None]

# Map sensor types to impact domains
_DOMAIN_MAP: dict[SensorType, ImpactDomain] = {
    SensorType.WATER_FLOW:     ImpactDomain.WATER,
    SensorType.WATER_QUALITY:  ImpactDomain.WATER,
    SensorType.SOIL_MOISTURE:  ImpactDomain.AGRICULTURE,
    SensorType.AIR_QUALITY:    ImpactDomain.ECOLOGY,
    SensorType.TEMPERATURE:    ImpactDomain.ECOLOGY,
    SensorType.HUMIDITY:       ImpactDomain.AGRICULTURE,
    SensorType.POWER_METER:    ImpactDomain.ENERGY,
    SensorType.GPS:            ImpactDomain.CITIES,
    SensorType.CAMERA:         ImpactDomain.CITIES,
    SensorType.CUSTOM:         ImpactDomain.ECONOMICS,
}


class SignalPipeline:
    def __init__(self, node_id: str):
        self._node_id = node_id
        self._handlers: list[SignalHandler] = []
        self._dropped = 0
        self._processed = 0

    def register_handler(self, handler: SignalHandler) -> None:
        self._handlers.append(handler)

    def ingest(self, reading: SensorReading) -> Signal | None:
        if not self._validate(reading):
            self._dropped += 1
            return None

        signal = self._convert(reading)
        for handler in self._handlers:
            try:
                handler(signal)
            except Exception as exc:
                log.warning("Signal handler error: %s", exc)

        self._processed += 1
        log.debug("Signal ingested [%s] sensor=%s value=%.3f %s",
                  signal.domain.value, reading.sensor_id, reading.value, reading.unit)
        return signal

    def stats(self) -> dict:
        return {"processed": self._processed, "dropped": self._dropped}

    # ------------------------------------------------------------------

    def _validate(self, reading: SensorReading) -> bool:
        if not reading.sensor_id:
            log.warning("Dropped reading: missing sensor_id")
            return False
        if reading.quality < 0.3:
            log.warning("Dropped reading from %s: quality %.2f below threshold",
                        reading.sensor_id, reading.quality)
            return False
        if reading.timestamp > datetime.utcnow():
            log.warning("Dropped reading from %s: future timestamp", reading.sensor_id)
            return False
        return True

    def _convert(self, reading: SensorReading) -> Signal:
        payload: dict = {
            "sensor_id": reading.sensor_id,
            "value": reading.value,
            "unit": reading.unit,
            "quality": reading.quality,
        }
        if reading.location:
            payload["geojson"] = reading.location.to_geojson()
        payload.update(reading.raw)

        return Signal(
            source=SignalSource.SENSOR,
            domain=_DOMAIN_MAP.get(reading.sensor_type, ImpactDomain.ECONOMICS),
            node_id=self._node_id,
            timestamp=reading.timestamp,
            payload=payload,
        )
