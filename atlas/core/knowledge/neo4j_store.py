"""
Atlas Sanctum — Neo4j Graph Store  (Phase VI)
Production knowledge graph backend.
Drop-in replacement for GraphStore (JSON-on-disk) — identical interface.

Requires: neo4j>=5.0  (pip install neo4j)
"""
from __future__ import annotations
import logging
from typing import Any

from atlas.core.knowledge.graph import KnowledgeGraph
from atlas.schemas.types import Entity, Relation

log = logging.getLogger("atlas.core.knowledge.neo4j")


class Neo4jGraphStore:
    """
    Persist and restore a KnowledgeGraph to/from Neo4j.
    Interface is identical to GraphStore — swap with a single line in AtlasCore.

    Usage:
        store = Neo4jGraphStore(uri="bolt://neo4j:7687", auth=("neo4j", "<password>"))
        graph = store.load()
        store.save(graph)
    """

    def __init__(self, uri: str, auth: tuple[str, str], database: str = "atlas"):
        self._uri = uri
        self._auth = auth
        self._database = database
        self._driver = None
        self._connect()

    def _connect(self) -> None:
        try:
            from neo4j import GraphDatabase  # type: ignore
            self._driver = GraphDatabase.driver(self._uri, auth=self._auth)
            self._driver.verify_connectivity()
            log.info("Neo4j connected: %s [db=%s]", self._uri, self._database)
        except ImportError:
            raise RuntimeError(
                "neo4j package not installed. Run: pip install neo4j"
            )
        except Exception as exc:
            raise RuntimeError(f"Neo4j connection failed: {exc}") from exc

    def save(self, graph: KnowledgeGraph) -> None:
        """Upsert all entities and relations into Neo4j."""
        with self._driver.session(database=self._database) as session:
            # Upsert entities
            for entity in graph._entities.values():
                session.run(
                    """
                    MERGE (e:Entity {id: $id})
                    SET e.kind = $kind, e.label = $label, e.properties = $props
                    """,
                    id=entity.id,
                    kind=entity.kind,
                    label=entity.label,
                    props=str(entity.properties),
                )
            # Upsert relations
            for rel in graph._relations.values():
                session.run(
                    """
                    MATCH (a:Entity {id: $src}), (b:Entity {id: $tgt})
                    MERGE (a)-[r:RELATION {id: $id}]->(b)
                    SET r.kind = $kind, r.weight = $weight
                    """,
                    id=rel.id,
                    src=rel.source_id,
                    tgt=rel.target_id,
                    kind=rel.kind,
                    weight=rel.weight,
                )
        log.info("Graph saved to Neo4j: %d entities, %d relations",
                 len(graph._entities), len(graph._relations))

    def load(self) -> KnowledgeGraph:
        """Load the full graph from Neo4j into memory."""
        graph = KnowledgeGraph()
        with self._driver.session(database=self._database) as session:
            for record in session.run("MATCH (e:Entity) RETURN e"):
                node = record["e"]
                graph.add_entity(Entity(
                    id=node["id"],
                    kind=node.get("kind", ""),
                    label=node.get("label", ""),
                    properties={},
                ))
            for record in session.run(
                "MATCH (a)-[r:RELATION]->(b) RETURN r, a.id AS src, b.id AS tgt"
            ):
                r = record["r"]
                graph.add_relation(Relation(
                    id=r["id"],
                    source_id=record["src"],
                    target_id=record["tgt"],
                    kind=r.get("kind", ""),
                    weight=r.get("weight", 1.0),
                ))
        log.info("Graph loaded from Neo4j: %d entities, %d relations",
                 len(graph._entities), len(graph._relations))
        return graph

    def close(self) -> None:
        if self._driver:
            self._driver.close()
