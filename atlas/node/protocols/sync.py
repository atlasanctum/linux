"""
Atlas Sanctum — Node Sync Protocol  (atlas/sync/v1)
Signs outbound SyncEnvelopes with the node's Ed25519 private key.
Verifies inbound envelope signatures before accepting payloads.
"""
from __future__ import annotations
import json
import logging
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey, Ed25519PublicKey,
)
from cryptography.hazmat.primitives.serialization import (
    Encoding, PublicFormat, PrivateFormat, NoEncryption,
)
from cryptography.exceptions import InvalidSignature

from atlas.schemas.phase3 import SyncEnvelope, SyncStatus

log = logging.getLogger("atlas.node.protocols.sync")

PROTOCOL_VERSION = "atlas/sync/v1"


class SyncProtocol:
    def __init__(self, identity_path: Path):
        data = json.loads(identity_path.read_text())
        priv_bytes = bytes.fromhex(data["private_key"])
        self._private_key = Ed25519PrivateKey.from_private_bytes(priv_bytes)
        self._public_key = self._private_key.public_key()
        self._node_id: str = data["id"]
        self._peer_keys: dict[str, Ed25519PublicKey] = {}   # node_id → public key

    def register_peer(self, node_id: str, public_key_hex: str) -> None:
        pub_bytes = bytes.fromhex(public_key_hex)
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
        # Reconstruct from raw bytes
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        import cryptography.hazmat.primitives.asymmetric.ed25519 as _ed
        key = _ed.Ed25519PublicKey.from_public_bytes(pub_bytes)
        self._peer_keys[node_id] = key
        log.info("Peer registered: %s", node_id)

    def sign(self, envelope: SyncEnvelope) -> SyncEnvelope:
        """Sign the envelope payload in-place and return it."""
        message = json.dumps(envelope.payload, sort_keys=True).encode()
        sig = self._private_key.sign(message)
        envelope.signature = sig.hex()
        envelope.origin_node_id = self._node_id
        return envelope

    def verify(self, envelope: SyncEnvelope) -> bool:
        """Verify the envelope signature against the registered peer key."""
        peer_key = self._peer_keys.get(envelope.origin_node_id)
        if peer_key is None:
            log.warning("No key for peer %s — rejecting envelope %s",
                        envelope.origin_node_id, envelope.id)
            return False
        try:
            message = json.dumps(envelope.payload, sort_keys=True).encode()
            peer_key.verify(bytes.fromhex(envelope.signature), message)
            return True
        except InvalidSignature:
            log.warning("Invalid signature on envelope %s from %s",
                        envelope.id, envelope.origin_node_id)
            return False
        except Exception as exc:
            log.error("Signature verification error: %s", exc)
            return False
