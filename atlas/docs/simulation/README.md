# Atlas Simulation Engine

The Atlas Simulation Engine allows nodes to explore possible futures before committing resources or actions.

## Design

```
Parameters
    ↓
Model Function
    ↓
SimulationRun (id, model, parameters, outputs, node_id, timestamp)
    ↓
Impact Ledger / Decision Layer
```

Models are pure functions: `(parameters: dict) → outputs: dict`. They are registered by name and can be swapped or extended without changing the engine.

## Built-in Models

| Model | Domain | Key Outputs |
|---|---|---|
| `water_demand` | Water | `daily_demand_litres`, `coverage_pct`, `deficit_litres` |
| `energy_balance` | Energy | `net_kwh`, `storage_kwh`, `surplus_pct` |
| `crop_yield` | Agriculture | `yield_kg_per_ha`, `water_stress_index` |
| `patient_flow` | Health | `daily_patients`, `occupancy_pct`, `overflow_risk` |
| `urban_capacity` | Cities | `congestion_index`, `throughput_pct` |

## Adding a Model

```python
from atlas.core.simulation.engine import SimulationEngine

def my_model(parameters: dict) -> dict:
    return {"result": parameters["input"] * 2}

engine = SimulationEngine(node_id="node-1")
engine.register("my_model", my_model)
run = engine.run("my_model", {"input": 5})
```

## Phase VI Extensions

- Federated simulation: run models across multiple nodes and aggregate results
- World model: shared civilization-scale parameter space
- Causal inference: identify intervention leverage points
- Reinforcement learning: agents that learn optimal policies through simulation
