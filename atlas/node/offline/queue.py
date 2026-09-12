"""
Atlas Sanctum — Offline Sync Queue
Durable JSONL queue that buffers SyncEnvelopes when a node is offline.
On reconnect, the queue replays pending envelopes to registered transports.

Design: append-only write, compacted on successful flush.
"""
from __future__ import annotations
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Callable

from atlas.schemas.phase3 import SyncEnvelope, SyncStatus

log = logging.getLogger("atlas.node.offline")

Transport = Callable[[SyncEnvelope], bool]   # returns True on success


class OfflineSyncQueue:
    def __init__(self, queue_path: Path, max_attempts: int = 5):
        self._path = queue_path
        self._max_attempts = max_attempts
        self._transports: list[Transport] = []
        queue_path.parent.mkdir(parents=True, exist_ok=True)

    def register_transport(self, transport: Transport) -> None:
        self._transports.append(transport)

    # ------------------------------------------------------------------
    # Enqueue
    # ------------------------------------------------------------------

    def enqueue(self, envelope: SyncEnvelope) -> None:
        envelope.status = SyncStatus.QUEUED
        self._append(envelope)
        log.debug("Queued envelope %s [type=%s]", envelope.id, envelope.payload_type)

    # ------------------------------------------------------------------
    # Flush — attempt to send all queued envelopes
    # ------------------------------------------------------------------

    def flush(self) -> dict:
        envelopes = self._load_pending()
        sent, failed, skipped = 0, 0, 0

        for env in envelopes:
            if env.attempts >= self._max_attempts:
                env.status = SyncStatus.FAILED
                skipped += 1
                continue
            success = self._send(env)
            if success:
                env.status = SyncStatus.ACKNOWLEDGED
                sent += 1
            else:
                env.attempts += 1
                failed += 1

        self._compact(envelopes)
        log.info("Sync flush: sent=%d failed=%d skipped=%d", sent, failed, skipped)
        return {"sent": sent, "failed": failed, "skipped": skipped}

    def pending_count(self) -> int:
        return len(self._load_pending())

    # ------------------------------------------------------------------

    def _send(self, envelope: SyncEnvelope) -> bool:
        for transport in self._transports:
            try:
                if transport(envelope):
                    return True
            except Exception as exc:
                log.warning("Transport error for %s: %s", envelope.id, exc)
        return False

    def _append(self, envelope: SyncEnvelope) -> None:
        with self._path.open("a") as f:
            f.write(json.dumps(self._serialise(envelope)) + "\n")

    def _load_pending(self) -> list[SyncEnvelope]:
        if not self._path.exists():
            return []
        envelopes = []
        for line in self._path.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            env = SyncEnvelope(
                id=data["id"],
                origin_node_id=data["origin_node_id"],
                target_node_id=data["target_node_id"],
                payload_type=data["payload_type"],
                payload=data["payload"],
                created_at=datetime.fromisoformat(data["created_at"]),
                status=SyncStatus(data["status"]),
                attempts=data["attempts"],
                signature=data.get("signature", ""),
            )
            if env.status in (SyncStatus.QUEUED, SyncStatus.FAILED) and env.attempts < self._max_attempts:
                envelopes.append(env)
        return envelopes

    def _compact(self, envelopes: list[SyncEnvelope]) -> None:
        """Rewrite queue keeping only un-acknowledged envelopes."""
        remaining = [e for e in envelopes if e.status != SyncStatus.ACKNOWLEDGED]
        with self._path.open("w") as f:
            for env in remaining:
                f.write(json.dumps(self._serialise(env)) + "\n")

    @staticmethod
    def _serialise(env: SyncEnvelope) -> dict:
        return {
            "id": env.id,
            "origin_node_id": env.origin_node_id,
            "target_node_id": env.target_node_id,
            "payload_type": env.payload_type,
            "payload": env.payload,
            "created_at": env.created_at.isoformat(),
            "status": env.status.value,
            "attempts": env.attempts,
            "signature": env.signature,
        }
