"""
Atlas Sanctum — Identity Manager
Generates and persists an Ed25519 keypair for a node.
"""
from __future__ import annotations
import json
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding, PublicFormat, PrivateFormat, NoEncryption,
)

from atlas.schemas.types import Identity


class IdentityManager:

    @staticmethod
    def load_or_create(path: Path) -> Identity:
        if path.exists():
            return IdentityManager._load(path)
        return IdentityManager._create(path)

    # ------------------------------------------------------------------
    @staticmethod
    def _create(path: Path) -> Identity:
        path.parent.mkdir(parents=True, exist_ok=True)
        private_key = Ed25519PrivateKey.generate()
        pub_hex = private_key.public_key().public_bytes(
            Encoding.Raw, PublicFormat.Raw
        ).hex()
        priv_hex = private_key.private_bytes(
            Encoding.Raw, PrivateFormat.Raw, NoEncryption()
        ).hex()
        identity = Identity(public_key=pub_hex)
        data = {
            "id": identity.id,
            "public_key": pub_hex,
            "private_key": priv_hex,          # stored locally only, never transmitted
            "created_at": identity.created_at.isoformat(),
        }
        path.write_text(json.dumps(data, indent=2))
        return identity

    @staticmethod
    def _load(path: Path) -> Identity:
        data = json.loads(path.read_text())
        identity = Identity(id=data["id"], public_key=data["public_key"])
        return identity
