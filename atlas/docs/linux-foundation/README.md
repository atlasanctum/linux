# Atlas Linux Foundation

Atlas Sanctum is built on Linux as its open, sovereign infrastructure layer.

## Why Linux

Linux provides the only credible foundation for a civilization-scale open intelligence substrate:

- **Open source** — auditable, forkable, community-governed
- **Ubiquitous** — runs on everything from a Raspberry Pi to a hyperscale data centre
- **Secure** — decades of hardening, SELinux, namespaces, cgroups, capabilities
- **Edge-capable** — minimal footprint deployments for field nodes
- **Container-native** — Docker and Kubernetes run on Linux primitives

## Atlas on Linux

```
Linux Kernel
    ↓
systemd / init
    ↓
Containers (Docker / Podman)
    ↓
Orchestration (Kubernetes / K3s)
    ↓
Atlas Node Runtime (Python 3.14)
    ↓
AtlasCore + Field Systems + API
```

## Deployment Targets

| Target | Runtime | Use Case |
|---|---|---|
| Raspberry Pi 4 / 5 | K3s + Python | Village edge node |
| Ubuntu Server 22.04+ | Docker Compose | Community node |
| Kubernetes cluster | Helm / manifests | Institutional node |
| Cloud VM (any) | Docker / K8s | Regional hub |

## Key Files

- `infrastructure/containers/Dockerfile` — Atlas node container image
- `infrastructure/containers/docker-compose.yml` — Local stack (node + postgres + neo4j)
- `infrastructure/kubernetes/node-deployment.yaml` — K8s deployment + PVC
- `infrastructure/linux/atlas-node.service` — systemd unit for bare-metal deployment
- `infrastructure/linux/sysctl-atlas.conf` — Kernel tuning for Atlas nodes
- `infrastructure/networking/wireguard-node.conf` — WireGuard mesh template
- `infrastructure/security/apparmor-atlas.profile` — AppArmor confinement profile

## Security Posture

Atlas nodes follow Linux security best practices:

- Run as non-root user (`atlas`, uid 1000)
- Read-only root filesystem where possible
- Capabilities dropped to minimum required
- AppArmor / SELinux profiles for confinement
- WireGuard for encrypted node-to-node transport
- Ed25519 identity per node, private key never leaves the node
