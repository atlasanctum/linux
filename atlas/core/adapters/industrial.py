"""
Atlas Sanctum — Industrial Adapter  (Phase IV)
Generic interface for ingesting data from industrial systems.
Supports: SCADA (stub), Modbus (stub), OPC-UA (stub), CSV file, JSON push.

Each adapter normalises readings into SensorReading objects for the pipeline.
"""
from __future__ import annotations
import csv
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Iterator

from atlas.schemas.phase3 import SensorReading, SensorType

log = logging.getLogger("atlas.core.adapters.industrial")


class IndustrialAdapter:
    """Base class — subclass or use the factory function below."""

    def read(self) -> Iterator[SensorReading]:
        raise NotImplementedError


class CSVAdapter(IndustrialAdapter):
    """
    Reads sensor readings from a CSV file.
    Expected columns: sensor_id, sensor_type, value, unit, quality, timestamp (ISO)
    """
    def __init__(self, path: Path, node_id: str = ""):
        self._path = path
        self._node_id = node_id

    def read(self) -> Iterator[SensorReading]:
        with self._path.open() as f:
            for row in csv.DictReader(f):
                try:
                    yield SensorReading(
                        sensor_id=row["sensor_id"],
                        sensor_type=SensorType(row.get("sensor_type", "custom")),
                        node_id=self._node_id,
                        value=float(row["value"]),
                        unit=row.get("unit", ""),
                        quality=float(row.get("quality", 1.0)),
                        timestamp=datetime.fromisoformat(row["timestamp"])
                        if "timestamp" in row else datetime.utcnow(),
                    )
                except Exception as exc:
                    log.warning("CSV row skipped: %s — %s", row, exc)


class JSONPushAdapter(IndustrialAdapter):
    """
    Accepts a list of raw JSON dicts (e.g. from an HTTP POST body or MQTT message).
    """
    def __init__(self, records: list[dict], node_id: str = ""):
        self._records = records
        self._node_id = node_id

    def read(self) -> Iterator[SensorReading]:
        for r in self._records:
            try:
                yield SensorReading(
                    sensor_id=r["sensor_id"],
                    sensor_type=SensorType(r.get("sensor_type", "custom")),
                    node_id=self._node_id,
                    value=float(r["value"]),
                    unit=r.get("unit", ""),
                    quality=float(r.get("quality", 1.0)),
                    raw=r.get("raw", {}),
                )
            except Exception as exc:
                log.warning("JSON record skipped: %s — %s", r, exc)


class ModbusStubAdapter(IndustrialAdapter):
    """
    Stub for Modbus TCP integration.
    Replace _fetch_registers() with pymodbus calls in production.
    """
    def __init__(self, host: str, port: int = 502, node_id: str = ""):
        self._host = host
        self._port = port
        self._node_id = node_id

    def read(self) -> Iterator[SensorReading]:
        log.info("Modbus stub: would connect to %s:%d", self._host, self._port)
        # Production: use pymodbus to read holding registers and yield SensorReadings
        return iter([])


def adapter_from_config(config: dict, node_id: str = "") -> IndustrialAdapter:
    """Factory: create an adapter from a config dict."""
    kind = config.get("type", "json")
    if kind == "csv":
        return CSVAdapter(Path(config["path"]), node_id=node_id)
    if kind == "modbus":
        return ModbusStubAdapter(config["host"], config.get("port", 502), node_id=node_id)
    if kind == "json":
        return JSONPushAdapter(config.get("records", []), node_id=node_id)
    raise ValueError(f"Unknown adapter type: {kind}")
