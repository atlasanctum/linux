# Atlas Storage Architecture

Atlas nodes use a layered storage strategy designed for sovereignty, durability, and offline resilience.

## Storage Layers

```
Hot (in-memory)
    KnowledgeGraph — entity/relation adjacency maps
    GeoIndex       — spatial feature index
    Agent state    — active task context

Warm (local disk)
    knowledge_graph.json   — JSON snapshot of graph (GraphStore)
    impact_ledger.jsonl    — append-only impact records
    offline_queue.jsonl    — pending sync envelopes
    node_identity.json     — Ed25519 keypair (private key never leaves node)

Cold (optional)
    PostgreSQL             — relational data, time-series signals
    Neo4j                  — production knowledge graph (Phase VI swap)
    Object storage         — datasets, experiment artifacts, field media
```

## Phase VI Swap Points

The `GraphStore` interface in `core/knowledge/store.py` is designed to swap to Neo4j with a single-line change:

```python
# Current (Phase I–V)
store = GraphStore(path=data_dir / "knowledge_graph.json")

# Phase VI
store = Neo4jGraphStore(uri="bolt://neo4j:7687", auth=("neo4j", "<password>"))
```

Both expose identical `save(graph)` and `load() → KnowledgeGraph` methods.

## Kubernetes Persistent Volumes

See `infrastructure/kubernetes/node-deployment.yaml` for the PVC configuration. Each Atlas node gets:

- `atlas-data` — 10Gi ReadWriteOnce for knowledge graph + ledger
- `atlas-logs` — 5Gi ReadWriteOnce for structured logs

## Backup Strategy

- Knowledge graph: snapshot on every `save_graph()` call + daily cron backup
- Impact ledger: JSONL is append-only; replicate to object storage daily
- Identity: Ed25519 private key backed up to encrypted offline storage only
