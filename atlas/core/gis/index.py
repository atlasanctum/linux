"""
Atlas Sanctum — GIS Layer
GeoIndex: spatial index for entities and signals.
GeoFeature: annotated GeoJSON feature.
Utilities: haversine distance, bounding-box filter.
"""
from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Any, Iterator

from atlas.schemas.phase3 import GeoPoint


@dataclass
class GeoFeature:
    id: str = ""
    kind: str = ""                # "entity" | "signal" | "opportunity" | "sensor"
    label: str = ""
    location: GeoPoint = field(default_factory=GeoPoint)
    properties: dict[str, Any] = field(default_factory=dict)

    def to_geojson(self) -> dict:
        return {
            "type": "Feature",
            "id": self.id,
            "geometry": self.location.to_geojson(),
            "properties": {"kind": self.kind, "label": self.label, **self.properties},
        }


class GeoIndex:
    """In-memory spatial index. Phase IV will swap this for PostGIS or H3."""

    def __init__(self):
        self._features: dict[str, GeoFeature] = {}

    def add(self, feature: GeoFeature) -> None:
        self._features[feature.id] = feature

    def get(self, feature_id: str) -> GeoFeature | None:
        return self._features.get(feature_id)

    def within_radius(self, centre: GeoPoint, radius_km: float) -> Iterator[GeoFeature]:
        for f in self._features.values():
            if haversine_km(centre, f.location) <= radius_km:
                yield f

    def within_bbox(
        self,
        min_lat: float, min_lon: float,
        max_lat: float, max_lon: float,
    ) -> Iterator[GeoFeature]:
        for f in self._features.values():
            lat, lon = f.location.latitude, f.location.longitude
            if min_lat <= lat <= max_lat and min_lon <= lon <= max_lon:
                yield f

    def to_geojson_collection(self) -> dict:
        return {
            "type": "FeatureCollection",
            "features": [f.to_geojson() for f in self._features.values()],
        }

    def count(self) -> int:
        return len(self._features)


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

_EARTH_RADIUS_KM = 6371.0


def haversine_km(a: GeoPoint, b: GeoPoint) -> float:
    """Great-circle distance between two GeoPoints in kilometres."""
    lat1, lon1 = math.radians(a.latitude), math.radians(a.longitude)
    lat2, lon2 = math.radians(b.latitude), math.radians(b.longitude)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * _EARTH_RADIUS_KM * math.asin(math.sqrt(h))
