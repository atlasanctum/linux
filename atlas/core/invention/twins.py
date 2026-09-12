"""
Atlas Sanctum — Digital Twin Engine  (Phase IV)
Maintains live state models of physical assets.
Syncs state from the signal pipeline, records history, runs experiments.
"""
from __future__ import annotations
import logging
from datetime import datetime
from typing import Any, Callable

from atlas.schemas.phase4 import (
    DigitalTwin, ExperimentRun, ExperimentStatus,
    PrototypeRun, PrototypeStatus, InventionProposal,
)
from atlas.schemas.types import Signal

log = logging.getLogger("atlas.core.invention.twins")

StateUpdater = Callable[[DigitalTwin, Signal], None]
ExperimentFn = Callable[[DigitalTwin, dict], dict]


class DigitalTwinEngine:
    def __init__(self, node_id: str = ""):
        self._twins: dict[str, DigitalTwin] = {}
        self._updaters: dict[str, StateUpdater] = {}
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
        """Update twin state from a signal and snapshot to history."""
        twin = self._twins.get(twin_id)
        if not twin:
            return
        updater = self._updaters.get(twin.model_type)
        if updater:
            # Snapshot state before update
            twin.history.append({
                "ts": twin.last_synced.isoformat(),
                "state": dict(twin.state),
            })
            updater(twin, signal)
            twin.last_synced = datetime.utcnow()
            log.debug("Twin '%s' synced from signal %s", twin.name, signal.id)

    def run_experiment(self, twin_id: str, hypothesis: str,
                       parameters: dict[str, Any],
                       experiment_fn: ExperimentFn) -> ExperimentRun:
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

    def history(self, twin_id: str) -> list[dict]:
        twin = self._twins.get(twin_id)
        return twin.history if twin else []


class PrototypeManager:
    """
    Tracks invention proposals through the full prototyping lifecycle:
    IDEA → DESIGNED → PROTOTYPING → TESTING → VALIDATED → SCALING
    """
    _TRANSITIONS: dict[PrototypeStatus, PrototypeStatus] = {
        PrototypeStatus.IDEA:        PrototypeStatus.DESIGNED,
        PrototypeStatus.DESIGNED:    PrototypeStatus.PROTOTYPING,
        PrototypeStatus.PROTOTYPING: PrototypeStatus.TESTING,
        PrototypeStatus.TESTING:     PrototypeStatus.VALIDATED,
        PrototypeStatus.VALIDATED:   PrototypeStatus.SCALING,
    }

    def __init__(self, node_id: str = ""):
        self._runs: dict[str, PrototypeRun] = {}
        self._node_id = node_id

    def start(self, proposal: InventionProposal) -> PrototypeRun:
        run = PrototypeRun(
            proposal_id=proposal.id,
            title=proposal.title,
            status=PrototypeStatus.IDEA,
            node_id=self._node_id,
        )
        self._runs[run.id] = run
        log.info("Prototype started: '%s' [IDEA]", run.title)
        return run

    def advance(self, run_id: str, notes: str = "") -> PrototypeRun | None:
        """Advance a prototype to the next stage."""
        run = self._runs.get(run_id)
        if not run:
            return None
        next_stage = self._TRANSITIONS.get(run.status)
        if not next_stage:
            log.info("Prototype '%s' already at terminal stage: %s",
                     run.title, run.status.value)
            return run
        run.stage_notes[run.status.value] = notes
        run.status = next_stage
        run.updated_at = datetime.utcnow()
        if next_stage == PrototypeStatus.VALIDATED:
            run.validated_at = datetime.utcnow()
        log.info("Prototype '%s' advanced to %s", run.title, next_stage.value)
        return run

    def get(self, run_id: str) -> PrototypeRun | None:
        return self._runs.get(run_id)

    def all(self) -> list[PrototypeRun]:
        return list(self._runs.values())

    def by_status(self, status: PrototypeStatus) -> list[PrototypeRun]:
        return [r for r in self._runs.values() if r.status == status]


# ---------------------------------------------------------------------------
# Built-in state updaters — one per field domain
# ---------------------------------------------------------------------------

def water_pump_updater(twin: DigitalTwin, signal: Signal) -> None:
    twin.state["flow_rate"] = signal.payload.get("value", twin.state.get("flow_rate", 0))
    twin.state["quality"] = signal.payload.get("quality", 1.0)
    twin.state["sensor_id"] = signal.payload.get("sensor_id", "")


def solar_array_updater(twin: DigitalTwin, signal: Signal) -> None:
    twin.state["output_kwh"] = signal.payload.get("value", twin.state.get("output_kwh", 0))
    twin.state["sensor_id"] = signal.payload.get("sensor_id", "")


def crop_field_updater(twin: DigitalTwin, signal: Signal) -> None:
    """Updates crop field twin from soil moisture, temperature, or humidity signals."""
    sensor_type = signal.payload.get("sensor_id", "")
    value = signal.payload.get("value", 0)
    if "soil" in sensor_type:
        twin.state["soil_moisture"] = value
    elif "temp" in sensor_type:
        twin.state["temperature_c"] = value
    elif "humidity" in sensor_type:
        twin.state["humidity_pct"] = value
    twin.state["last_sensor"] = sensor_type
    # Recompute stress index: optimal soil moisture 0.25–0.40
    moisture = twin.state.get("soil_moisture", 0.3)
    twin.state["water_stress_index"] = round(
        max(0.0, 1.0 - moisture / 0.35), 3
    )


def clinic_updater(twin: DigitalTwin, signal: Signal) -> None:
    """Updates clinic twin from occupancy or wait-time sensors."""
    value = signal.payload.get("value", 0)
    raw = signal.payload.get("raw", {})
    if "occupancy" in signal.payload.get("sensor_id", ""):
        twin.state["current_patients"] = value
        twin.state["occupancy_rate"] = raw.get("occupancy_rate",
                                                value / twin.state.get("capacity", 20))
    elif "wait" in signal.payload.get("sensor_id", ""):
        twin.state["avg_wait_min"] = value
        twin.state["over_target"] = value > raw.get("target_wait_min", 30)


def workshop_updater(twin: DigitalTwin, signal: Signal) -> None:
    """Updates manufacturing workshop twin from utilisation sensors."""
    twin.state["utilisation"] = signal.payload.get("value", twin.state.get("utilisation", 0))
    twin.state["sensor_id"] = signal.payload.get("sensor_id", "")
    twin.state["idle"] = twin.state["utilisation"] < 0.3


def traffic_junction_updater(twin: DigitalTwin, signal: Signal) -> None:
    """Updates road junction twin from GPS/traffic count sensors."""
    twin.state["vehicles_per_hour"] = signal.payload.get(
        "value", twin.state.get("vehicles_per_hour", 0)
    )
    capacity = twin.state.get("capacity_vph", 1500)
    twin.state["congestion_ratio"] = round(
        twin.state["vehicles_per_hour"] / capacity, 3
    )
    twin.state["congested"] = twin.state["congestion_ratio"] > 0.85
