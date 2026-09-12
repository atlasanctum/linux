"""
Atlas Sanctum — Knowledge Graph Persistence
JSON-on-disk store for Phase II. Interface is identical to what Neo4j
will expose in Phase III, so the swap is a single-line change.
"""
from __future__ import annotations
import json
from pathlib import Path

from atlas.core.knowledge.graph import KnowledgeGraph
from atlas.schemas.types import Entity, Relation


class GraphStore:
    """Persist and restore a KnowledgeGraph to/from a JSON file."""

    def __init__(self, path: Path):
        self._path = path

    def save(self, graph: KnowledgeGraph) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "entities": [
                {"id": e.id, "kind": e.kind, "label": e.label, "properties": e.properties}
                for e in graph._entities.values()
            ],
            "relations": [
                {
                    "id": r.id, "source_id": r.source_id, "target_id": r.target_id,
                    "kind": r.kind, "weight": r.weight, "properties": r.properties,
                }
                for r in graph._relations.values()
            ],
        }
        self._path.write_text(json.dumps(data, indent=2))

    def load(self) -> KnowledgeGraph:
        graph = KnowledgeGraph()
        if not self._path.exists():
            return graph
        data = json.loads(self._path.read_text())
        for e in data.get("entities", []):
            graph.add_entity(Entity(**e))
        for r in data.get("relations", []):
            graph.add_relation(Relation(**r))
        return graph
