"""
Atlas Sanctum — Edge Node Runner  (Phase III)
Starts the Atlas Node with:
  - AtlasCore (intelligence)
  - SignalPipeline (sensor ingestion)
  - GeoIndex (spatial)
  - OfflineSyncQueue (resilience)
  - REST API on 0.0.0.0:7700

Usage:
    python -m atlas.node.edge.runner --name "Nairobi-01" --role edge --port 7700
"""
from __future__ import annotations
import argparse
import logging
import signal
import sys
import threading
from pathlib import Path

from atlas.schemas.types import NodeConfig, NodeRole
from atlas.node.identity.manager import IdentityManager
from atlas.core.intelligence.core import AtlasCore
from atlas.core.signals.pipeline import SignalPipeline
from atlas.core.gis.index import GeoIndex
from atlas.node.offline.queue import OfflineSyncQueue
from atlas.node.protocols.heartbeat import Heartbeat

log = logging.getLogger("atlas.edge")
STATE_DIR = Path.home() / ".atlas" / "node"


def run(name: str, role: str, location: str, port: int) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)

    identity = IdentityManager.load_or_create(STATE_DIR / "identity.json")
    config = NodeConfig(
        name=name,
        role=NodeRole(role),
        location=location,
        identity=identity,
    )

    core = AtlasCore(node_id=config.id, data_dir=STATE_DIR / "core")
    pipeline = SignalPipeline(node_id=config.id)
    geo = GeoIndex()
    sync_queue = OfflineSyncQueue(STATE_DIR / "sync_queue.jsonl")
    heartbeat = Heartbeat(node_id=config.id, interval=30)

    # Route validated signals into the knowledge graph as entities
    def _signal_to_graph(sig):
        from atlas.schemas.types import Entity
        entity = Entity(
            id=sig.id,
            kind="signal",
            label=f"{sig.source.value}:{sig.domain.value}",
            properties=sig.payload,
        )
        core.graph.add_entity(entity)

    pipeline.register_handler(_signal_to_graph)

    log.info("Atlas Edge Node '%s' starting [id=%s port=%d]", name, config.id, port)

    # Start heartbeat in background thread
    _running = threading.Event()
    _running.set()

    def _hb_loop():
        import time
        while _running.is_set():
            heartbeat.tick()
            time.sleep(1)

    hb_thread = threading.Thread(target=_hb_loop, daemon=True)
    hb_thread.start()

    def _shutdown(sig, frame):
        log.info("Shutting down...")
        _running.clear()
        core.save_graph()
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    # Start API server
    try:
        import uvicorn
        from atlas.node.api.app import create_app
        app = create_app(core, pipeline, geo)
        uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
    except ImportError:
        log.warning("uvicorn/fastapi not installed — running headless (no API)")
        import time
        while _running.is_set():
            time.sleep(1)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    )
    p = argparse.ArgumentParser(description="Atlas Edge Node")
    p.add_argument("--name", default="atlas-edge-01")
    p.add_argument("--role", default="edge", choices=[r.value for r in NodeRole])
    p.add_argument("--location", default="")
    p.add_argument("--port", type=int, default=7700)
    args = p.parse_args()
    run(args.name, args.role, args.location, args.port)


if __name__ == "__main__":
    main()
