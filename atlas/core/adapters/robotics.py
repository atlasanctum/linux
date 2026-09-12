"""
Atlas Sanctum — Robotics Adapter  (Phase IV)
Interface for dispatching tasks to robotic systems and receiving sensor data back.

Supports:
  - ROS 2 stub (replace _ros_dispatch with rclpy calls)
  - HTTP robot API stub (replace _http_dispatch with requests calls)
  - Simulation mode (returns synthetic readings for testing)

Each task produces SensorReadings that feed back into the signal pipeline.
"""
from __future__ import annotations
import logging
import uuid
from datetime import datetime
from typing import Iterator

from atlas.schemas.phase4 import RoboticsTask, RoboticsTaskStatus
from atlas.schemas.phase3 import SensorReading, SensorType

log = logging.getLogger("atlas.core.adapters.robotics")


class RoboticsAdapter:
    """
    Base robotics adapter. Subclass for ROS 2, HTTP, or simulation backends.
    """

    def dispatch(self, task: RoboticsTask) -> RoboticsTask:
        raise NotImplementedError

    def readings(self, task: RoboticsTask) -> Iterator[SensorReading]:
        raise NotImplementedError


class SimulationRoboticsAdapter(RoboticsAdapter):
    """
    Simulation-mode adapter for testing and field prototyping.
    Returns synthetic sensor readings based on task type.
    No physical robot required.
    """

    def __init__(self, node_id: str = ""):
        self._node_id = node_id
        self._tasks: dict[str, RoboticsTask] = {}

    def dispatch(self, task: RoboticsTask) -> RoboticsTask:
        task.status = RoboticsTaskStatus.RUNNING
        log.info("Robotics task dispatched [sim]: %s / %s", task.robot_id, task.task_type)

        try:
            task.result = self._simulate(task)
            task.status = RoboticsTaskStatus.COMPLETE
        except Exception as exc:
            task.result = {"error": str(exc)}
            task.status = RoboticsTaskStatus.FAILED
            log.error("Robotics task failed: %s", exc)
        finally:
            task.completed_at = datetime.utcnow()

        self._tasks[task.id] = task
        return task

    def readings(self, task: RoboticsTask) -> Iterator[SensorReading]:
        """Yield SensorReadings extracted from a completed task result."""
        if task.status != RoboticsTaskStatus.COMPLETE:
            return
        for reading_dict in task.result.get("readings", []):
            try:
                yield SensorReading(
                    sensor_id=f"{task.robot_id}:{reading_dict['sensor_id']}",
                    sensor_type=SensorType(reading_dict.get("sensor_type", "custom")),
                    node_id=self._node_id,
                    value=float(reading_dict["value"]),
                    unit=reading_dict.get("unit", ""),
                    quality=float(reading_dict.get("quality", 0.85)),
                    raw=reading_dict.get("raw", {}),
                )
            except Exception as exc:
                log.warning("Skipping reading from task %s: %s", task.id, exc)

    def get_task(self, task_id: str) -> RoboticsTask | None:
        return self._tasks.get(task_id)

    def all_tasks(self) -> list[RoboticsTask]:
        return list(self._tasks.values())

    # ------------------------------------------------------------------

    def _simulate(self, task: RoboticsTask) -> dict:
        """Generate synthetic results based on task type."""
        t = task.task_type
        if t == "inspect":
            return {
                "findings": "No structural anomalies detected",
                "readings": [
                    {"sensor_id": "visual", "sensor_type": "custom",
                     "value": 1.0, "unit": "ok", "quality": 0.9},
                ],
            }
        if t == "sample":
            return {
                "sample_id": str(uuid.uuid4())[:8],
                "readings": [
                    {"sensor_id": "water_quality", "sensor_type": "water_quality",
                     "value": 0.4, "unit": "NTU", "quality": 0.92,
                     "raw": {"ph": 7.0, "turbidity_ntu": 0.4}},
                ],
            }
        if t == "survey":
            return {
                "area_covered_m2": task.parameters.get("area_m2", 1000),
                "readings": [
                    {"sensor_id": "gps_survey", "sensor_type": "gps",
                     "value": task.parameters.get("area_m2", 1000),
                     "unit": "m2", "quality": 0.95},
                ],
            }
        if t == "actuate":
            return {
                "actuated": True,
                "target": task.parameters.get("target", "unknown"),
                "readings": [],
            }
        return {"status": "completed", "readings": []}


class ROSStubAdapter(RoboticsAdapter):
    """
    Stub for ROS 2 integration.
    Replace _ros_dispatch with rclpy publisher/service calls in production.
    Requires: pip install rclpy  (inside a ROS 2 environment)
    """

    def __init__(self, robot_id: str, node_id: str = ""):
        self._robot_id = robot_id
        self._node_id = node_id

    def dispatch(self, task: RoboticsTask) -> RoboticsTask:
        log.info("ROS stub: would publish task %s to robot %s",
                 task.task_type, self._robot_id)
        # Production: rclpy.init(); node.create_publisher(...).publish(task_msg)
        task.status = RoboticsTaskStatus.QUEUED
        return task

    def readings(self, task: RoboticsTask) -> Iterator[SensorReading]:
        # Production: subscribe to /atlas/readings topic and yield SensorReadings
        return iter([])


def robotics_adapter_from_config(config: dict, node_id: str = "") -> RoboticsAdapter:
    """Factory: create a robotics adapter from a config dict."""
    kind = config.get("type", "simulation")
    if kind == "simulation":
        return SimulationRoboticsAdapter(node_id=node_id)
    if kind == "ros":
        return ROSStubAdapter(config.get("robot_id", "robot-01"), node_id=node_id)
    raise ValueError(f"Unknown robotics adapter type: {kind}")
