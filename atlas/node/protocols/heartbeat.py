"""
Atlas Sanctum — Heartbeat Protocol
Emits a periodic liveness signal from a node.
Protocol format is JSON over stdout / future: UDP multicast or MQTT.
"""
from __future__ import annotations
import json
import logging
import time
from datetime import datetime

log = logging.getLogger("atlas.node.heartbeat")

PROTOCOL_VERSION = "atlas/heartbeat/v1"


class Heartbeat:
    def __init__(self, node_id: str, interval: int = 30):
        self.node_id = node_id
        self.interval = interval          # seconds between beats
        self._last_beat: float = 0.0
        self._sequence: int = 0

    def tick(self) -> None:
        now = time.monotonic()
        if now - self._last_beat >= self.interval:
            self._emit()
            self._last_beat = now

    # ------------------------------------------------------------------
    def _emit(self) -> None:
        self._sequence += 1
        beat = {
            "protocol": PROTOCOL_VERSION,
            "node_id": self.node_id,
            "seq": self._sequence,
            "ts": datetime.utcnow().isoformat() + "Z",
        }
        log.info("♥  %s", json.dumps(beat))
