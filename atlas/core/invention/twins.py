"""
Atlas Sanctum — Digital Twin Engine  (Phase IV)
Maintains live state models of physical assets.
Syncs state from the signal pipeline, runs experiments against the model.
"""
from __future__ import annotations
import logging
from datetime import datetime
from typing import Any, Callable

from atlas.schemas.phase4 import DigitalTwin, ExperimentRun, ExperimentStatus
from atlas.schemas.types import Signal

log = logging.getLogger("atlas.core.invention.twins")

StateUpdater = Callable[[DigitalTwin, Signal], None]


class DigitalTwinEngine:
    def __init__(self, node_id: str = ""):
        self._twins: dict[str, DigitalTwin] = {}
        self._updaters: dict[str, StateUpdater] = {}   # model_type → updater fn
        self._node_id = node_id

    def register_updater(self, model_type: str, fn: StateUpdater) -> None:
        self._updaters[model_type] = fn

    def create(self, name: str, asset_id: str, model_type: str,
               initial_state: dict[str, Any] | None = None) -> DigitalTwin:
        twin = DigitalTwin(
            name=name, asset_id=asset_id, model_type=model_type,
            state=initial_state or {}, node_id=self._node_id,
        )
        self._twins[twin.id] = twin
        log.info("Digital twin created: %s [%s]", name, model_type)
        return twin

    def sync(self, twin_id: str, signal: Signal) -> None:
        twin = self._twins.get(twin_id)
        if not twin:
            return
        updater = self._updaters.get(twin.model_type)
        if updater:
            updater(twin, signal)
            twin.last_synced = datetime.utcnow()
            log.debug("Twin '%s' synced from signal %s", twin.name, signal.id)

    def run_experiment(self, twin_id: str, hypothesis: str,
                       parameters: dict[str, Any],
                       experiment_fn: Callable[[DigitalTwin, dict], dict]) -> ExperimentRun:
        twin = self._twins.get(twin_id)
        exp = ExperimentRun(
            name=f"{twin.name if twin else twin_id} — {hypothesis[:40]}",
            twin_id=twin_id,
            hypothesis=hypothesis,
            parameters=parameters,
            node_id=self._node_id,
        )
        if not twin:
            exp.status = ExperimentStatus.FAILED
            exp.result = {"error": f"twin {twin_id} not found"}
            return exp

        exp.status = ExperimentStatus.RUNNING
        exp.started_at = datetime.utcnow()
        try:
            exp.result = experiment_fn(twin, parameters)
            exp.status = ExperimentStatus.COMPLETE
            log.info("Experiment '%s' complete: %s", exp.name, exp.result)
        except Exception as exc:
            exp.status = ExperimentStatus.FAILED
            exp.result = {"error": str(exc)}
            log.error("Experiment '%s' failed: %s", exp.name, exc)
        finally:
            exp.completed_at = datetime.utcnow()
        return exp

    def get(self, twin_id: str) -> DigitalTwin | None:
        return self._twins.get(twin_id)

    def all(self) -> list[DigitalTwin]:
        return list(self._twins.values())


# ---------------------------------------------------------------------------
# Built-in state updaters
# ---------------------------------------------------------------------------

def water_pump_updater(twin: DigitalTwin, signal: Signal) -> None:
    twin.state["flow_rate"] = signal.payload.get("value", twin.state.get("flow_rate", 0))
    twin.state["quality"] = signal.payload.get("quality", 1.0)
    twin.state["sensor_id"] = signal.payload.get("sensor_id", "")


def solar_array_updater(twin: DigitalTwin, signal: Signal) -> None:
    twin.state["output_kwh"] = signal.payload.get("value", twin.state.get("output_kwh", 0))
    twin.state["sensor_id"] = signal.payload.get("sensor_id", "")
