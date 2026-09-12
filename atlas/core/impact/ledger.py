"""
Atlas Sanctum — Impact Ledger
Append-only record of real-world outcome measurements.
"""
from __future__ import annotations
import json
import logging
from datetime import datetime
from pathlib import Path

from atlas.schemas.types import ImpactRecord, ImpactDomain

log = logging.getLogger("atlas.core.impact")


class ImpactLedger:
    def __init__(self, store_path: Path | None = None):
        self._records: list[ImpactRecord] = []
        self._store_path = store_path

    def record(self, entry: ImpactRecord) -> None:
        self._records.append(entry)
        log.info("Impact recorded: [%s] %s = %.2f %s",
                 entry.domain.value, entry.metric, entry.value, entry.unit)
        if self._store_path:
            self._append_to_disk(entry)

    def query(
        self,
        domain: ImpactDomain | None = None,
        opportunity_id: str | None = None,
        since: datetime | None = None,
    ) -> list[ImpactRecord]:
        results = self._records
        if domain:
            results = [r for r in results if r.domain == domain]
        if opportunity_id:
            results = [r for r in results if r.opportunity_id == opportunity_id]
        if since:
            results = [r for r in results if r.measured_at >= since]
        return results

    def summary(self) -> dict:
        by_domain: dict[str, list[float]] = {}
        for r in self._records:
            by_domain.setdefault(r.domain.value, []).append(r.value)
        return {d: {"count": len(v), "total": sum(v)} for d, v in by_domain.items()}

    # ------------------------------------------------------------------
    def _append_to_disk(self, entry: ImpactRecord) -> None:
        self._store_path.parent.mkdir(parents=True, exist_ok=True)
        with self._store_path.open("a") as f:
            f.write(json.dumps({
                "id": entry.id,
                "opportunity_id": entry.opportunity_id,
                "domain": entry.domain.value,
                "metric": entry.metric,
                "value": entry.value,
                "unit": entry.unit,
                "measured_at": entry.measured_at.isoformat(),
                "node_id": entry.node_id,
                "notes": entry.notes,
            }) + "\n")
