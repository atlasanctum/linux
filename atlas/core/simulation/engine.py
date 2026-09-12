"""
Atlas Sanctum — Simulation Engine
Phase II: run registered models against parameter sets, record results.

A SimulationModel is a callable:
    (parameters: dict) -> dict   # returns result dict

Models are registered by name. The engine runs them, tracks status,
and stores results in SimulationRun records.
"""
from __future__ import annotations
import logging
from datetime import datetime
from typing import Any, Callable

from atlas.schemas.phase2 import SimulationRun, SimulationStatus

log = logging.getLogger("atlas.core.simulation")

SimulationModel = Callable[[dict[str, Any]], dict[str, Any]]


class SimulationEngine:
    def __init__(self, node_id: str = ""):
        self._models: dict[str, SimulationModel] = {}
        self._runs: dict[str, SimulationRun] = {}
        self._node_id = node_id

    def register(self, name: str, model: SimulationModel) -> None:
        self._models[name] = model
        log.info("Simulation model registered: %s", name)

    def run(self, name: str, parameters: dict[str, Any], label: str = "") -> SimulationRun:
        sim = SimulationRun(
            name=label or name,
            model=name,
            parameters=parameters,
            node_id=self._node_id,
        )
        self._runs[sim.id] = sim

        model = self._models.get(name)
        if model is None:
            sim.status = SimulationStatus.FAILED
            sim.result = {"error": f"no model named '{name}'"}
            return sim

        sim.status = SimulationStatus.RUNNING
        sim.started_at = datetime.utcnow()
        try:
            sim.result = model(parameters)
            sim.status = SimulationStatus.COMPLETE
            log.info("Simulation '%s' complete: %s", sim.name, sim.result)
        except Exception as exc:
            sim.status = SimulationStatus.FAILED
            sim.result = {"error": str(exc)}
            log.error("Simulation '%s' failed: %s", sim.name, exc)
        finally:
            sim.completed_at = datetime.utcnow()

        return sim

    def get_run(self, run_id: str) -> SimulationRun | None:
        return self._runs.get(run_id)

    def all_runs(self) -> list[SimulationRun]:
        return list(self._runs.values())


# ---------------------------------------------------------------------------
# Built-in simulation models
# ---------------------------------------------------------------------------

def water_demand_model(params: dict[str, Any]) -> dict[str, Any]:
    """
    Simple water demand projection.
    params: population, daily_litres_per_person, days, loss_factor (0–1)
    """
    pop = float(params.get("population", 1000))
    lpd = float(params.get("daily_litres_per_person", 50))
    days = int(params.get("days", 30))
    loss = float(params.get("loss_factor", 0.15))

    gross = pop * lpd * days
    net = gross * (1 - loss)
    return {
        "gross_litres": round(gross),
        "net_litres": round(net),
        "loss_litres": round(gross - net),
        "days": days,
        "population": pop,
    }


def energy_balance_model(params: dict[str, Any]) -> dict[str, Any]:
    """
    Simple renewable energy balance.
    params: generation_kwh_day, storage_kwh, demand_kwh_day, days
    """
    gen = float(params.get("generation_kwh_day", 100))
    storage = float(params.get("storage_kwh", 50))
    demand = float(params.get("demand_kwh_day", 80))
    days = int(params.get("days", 30))

    daily_balance = gen - demand
    surplus_days = sum(1 for _ in range(days) if daily_balance >= 0)
    deficit_days = days - surplus_days
    total_surplus = max(0.0, daily_balance * surplus_days)
    total_deficit = max(0.0, -daily_balance * deficit_days)

    return {
        "daily_balance_kwh": round(daily_balance, 2),
        "surplus_days": surplus_days,
        "deficit_days": deficit_days,
        "total_surplus_kwh": round(total_surplus, 2),
        "total_deficit_kwh": round(total_deficit, 2),
        "storage_covers_deficit": storage >= total_deficit,
    }
