"""
Atlas Sanctum — Project Marketplace  (Phase V)
Listings for needs, resources, skills, and projects.
Nodes publish listings; the marketplace matches them.
"""
from __future__ import annotations
import logging
from typing import Iterator

from atlas.schemas.phase5 import MarketplaceListing, ListingStatus

log = logging.getLogger("atlas.core.coordination.marketplace")


class Marketplace:
    def __init__(self):
        self._listings: dict[str, MarketplaceListing] = {}

    def publish(self, listing: MarketplaceListing) -> None:
        self._listings[listing.id] = listing
        log.info("Listing published: [%s] %s (%s)", listing.kind, listing.title, listing.domain)

    def search(self, kind: str | None = None, domain: str | None = None,
               status: ListingStatus = ListingStatus.OPEN) -> list[MarketplaceListing]:
        results = [l for l in self._listings.values() if l.status == status]
        if kind:
            results = [l for l in results if l.kind == kind]
        if domain:
            results = [l for l in results if l.domain == domain]
        return results

    def match(self, need_id: str, resource_id: str) -> bool:
        """Mark a need and resource as matched."""
        need = self._listings.get(need_id)
        resource = self._listings.get(resource_id)
        if not need or not resource:
            return False
        if need.domain != resource.domain:
            log.warning("Domain mismatch: %s vs %s", need.domain, resource.domain)
            return False
        need.status = ListingStatus.MATCHED
        resource.status = ListingStatus.MATCHED
        log.info("Matched: '%s' ↔ '%s'", need.title, resource.title)
        return True

    def stats(self) -> dict:
        by_kind: dict[str, int] = {}
        for l in self._listings.values():
            by_kind[l.kind] = by_kind.get(l.kind, 0) + 1
        return {"total": len(self._listings), "by_kind": by_kind}
