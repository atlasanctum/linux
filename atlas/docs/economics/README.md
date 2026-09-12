# Atlas Regenerative Economic Layer

Atlas treats economics as a coordination mechanism in service of human and ecological outcomes — not as an end in itself.

## The Coordination Loop

```
Capital
    ↓
Projects (CoordinationEngine)
    ↓
Infrastructure / Execution
    ↓
Outcomes
    ↓
Impact Ledger (measurement)
    ↓
Reinvestment
    ↺
```

## Components

### CoordinationEngine (`core/coordination/engine.py`)
- Creates and manages projects through their lifecycle: `proposed → funded → active → complete`
- Policy-gated capital allocation: every allocation must pass `human_oversight_required`
- Tracks allocated vs budget, updates project status automatically

### Marketplace (`core/coordination/marketplace.py`)
- Nodes publish needs, resources, skills, and projects as `MarketplaceListing` objects
- Search by domain, kind, or keyword
- Match listings across nodes to surface coordination opportunities

### FederationEngine (`core/federation/engine.py`)
- Regional networks of Atlas nodes
- Nodes share anonymised summaries — raw data never leaves the origin node
- `network_intelligence()` aggregates peer summaries for regional decision-making

## Policy Gate

All capital allocation is blocked by default until a human approves:

```yaml
# core/policy/rules.yaml
- name: no_autonomous_capital_allocation
  condition: "context.get('amount_usd', 0) > 0"
  action: deny
  reason: "Capital allocation requires human approval."
```

The `human_approved` flag on `CapitalAllocation` must be set explicitly.

## Phase VI Extensions

- Impact bonds: programmable capital with outcome-linked disbursement
- Cross-node capital pooling: regional investment vehicles
- Transparent allocation ledger: public audit trail for all capital flows
- Regenerative finance primitives: returns tied to ecological and social outcomes
