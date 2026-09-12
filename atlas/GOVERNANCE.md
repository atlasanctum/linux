# Governance

Atlas Sanctum is an open ecosystem. Governance exists to protect the mission,
not to concentrate control.

## Principles

- **Open stewardship** — technical decisions are made transparently
- **Protocol evolution** — changes to open protocols require community review
- **AI safety** — AI agents operate within policy boundaries with human oversight
- **Data sovereignty** — communities retain ownership of their data
- **Accountability** — all significant actions are auditable
- **Conflict resolution** — disputes are resolved through documented process
- **Public-interest safeguards** — Atlas must not be weaponized against the communities it serves

## Decision Process

1. Proposals are submitted to `community/proposals/`
2. A review period of at least 14 days applies to protocol changes
3. Security-critical changes may be fast-tracked with maintainer consensus
4. All accepted changes are recorded in the changelog

## AI Governance

AI agents within Atlas operate under the Policy Engine.
No agent may take a high-impact action without a passing `human_oversight_required` policy check.
Model governance (versioning, evaluation, retirement) is documented in `docs/agents/`.
