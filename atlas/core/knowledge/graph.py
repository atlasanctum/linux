"""
Atlas Sanctum — Knowledge Graph
Minimal in-memory graph of entities and relations.
Designed to be persisted to a graph database (Neo4j / Kuzu) in later phases.
"""
from __future__ import annotations
from collections import defaultdict
from typing import Iterator

from atlas.schemas.types import Entity, Relation


class KnowledgeGraph:
    def __init__(self):
        self._entities: dict[str, Entity] = {}
        self._relations: dict[str, Relation] = {}
        self._adj: dict[str, list[str]] = defaultdict(list)   # entity_id → [relation_id]

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def add_entity(self, entity: Entity) -> None:
        self._entities[entity.id] = entity

    def add_relation(self, relation: Relation) -> None:
        self._relations[relation.id] = relation
        self._adj[relation.source_id].append(relation.id)

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def get_entity(self, entity_id: str) -> Entity | None:
        return self._entities.get(entity_id)

    def neighbors(self, entity_id: str) -> Iterator[Entity]:
        for rel_id in self._adj.get(entity_id, []):
            rel = self._relations[rel_id]
            target = self._entities.get(rel.target_id)
            if target:
                yield target

    def relations_from(self, entity_id: str) -> Iterator[Relation]:
        for rel_id in self._adj.get(entity_id, []):
            yield self._relations[rel_id]

    def find_entities(self, kind: str) -> Iterator[Entity]:
        for e in self._entities.values():
            if e.kind == kind:
                yield e

    # ------------------------------------------------------------------
    def stats(self) -> dict:
        return {
            "entities": len(self._entities),
            "relations": len(self._relations),
        }
