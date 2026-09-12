# Security

Atlas Sanctum is designed around the following security principles:

- **Least privilege** — every component requests only the permissions it needs
- **Zero trust** — no implicit trust between nodes; all communication is authenticated
- **Encrypted communications** — TLS 1.3+ for all inter-node traffic
- **Strong identity** — Ed25519 keypairs per node; no shared secrets
- **Auditable actions** — all policy decisions and impact records are append-only
- **Data minimization** — collect only what is necessary; enforce via policy engine
- **Secure defaults** — systems fail closed, not open
- **Human oversight** — high-impact actions require explicit human approval

## Reporting a Vulnerability

Open a confidential issue or email the maintainers directly.

Do not disclose security vulnerabilities publicly until a fix is available.

## Threat Model

Atlas nodes may operate in low-trust environments (edge, offline, community).
The identity and protocol layers are designed to remain secure without
continuous connectivity to a central authority.
