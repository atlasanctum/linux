"""
Atlas Sanctum — Atlas Node
The minimal runnable unit of the Atlas network.

Usage:
    python node.py --name "Nairobi-01" --role edge --location "Nairobi, Kenya"
"""
from __future__ import annotations
import argparse
import json
import logging
import signal
import sys
import time
from datetime import datetime
from pathlib import Path

from atlas.schemas.types import NodeConfig, NodeRole, Identity
from atlas.node.identity.manager import IdentityManager
from atlas.node.protocols.heartbeat import Heartbeat

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
log = logging.getLogger("atlas.node")

STATE_DIR = Path.home() / ".atlas" / "node"


class AtlasNode:
    def __init__(self, config: NodeConfig):
        self.config = config
        self._running = False
        self._heartbeat = Heartbeat(node_id=config.id, interval=30)

    # ------------------------------------------------------------------
    def start(self) -> None:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        self._persist_config()
        self._running = True
        log.info("Atlas Node '%s' started  [role=%s  id=%s]",
                 self.config.name, self.config.role.value, self.config.id)
        self._loop()

    def stop(self) -> None:
        self._running = False
        log.info("Atlas Node '%s' stopping.", self.config.name)

    # ------------------------------------------------------------------
    def _loop(self) -> None:
        while self._running:
            self._heartbeat.tick()
            time.sleep(1)

    def _persist_config(self) -> None:
        path = STATE_DIR / "config.json"
        data = {
            "id": self.config.id,
            "name": self.config.name,
            "role": self.config.role.value,
            "location": self.config.location,
            "offline_capable": self.config.offline_capable,
            "created_at": self.config.created_at.isoformat(),
            "identity_id": self.config.identity.id if self.config.identity else None,
        }
        path.write_text(json.dumps(data, indent=2))
        log.info("Node config persisted → %s", path)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Atlas Sanctum Node")
    p.add_argument("--name", default="atlas-node-01")
    p.add_argument("--role", default="edge", choices=[r.value for r in NodeRole])
    p.add_argument("--location", default="")
    p.add_argument("--offline", action="store_true", default=True)
    return p.parse_args()


def main() -> None:
    args = _parse_args()

    identity = IdentityManager.load_or_create(STATE_DIR / "identity.json")
    config = NodeConfig(
        name=args.name,
        role=NodeRole(args.role),
        location=args.location,
        identity=identity,
        offline_capable=args.offline,
    )

    node = AtlasNode(config)

    def _shutdown(sig, frame):
        node.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    node.start()


if __name__ == "__main__":
    main()
