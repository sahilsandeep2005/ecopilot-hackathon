from __future__ import annotations

from typing import Any

from agent.schemas import ControlAction
from energyplus.handle_registry import HandleRegistry, ScheduleHandle


class ActuatorWriter:
    def __init__(self, api: Any, registry: HandleRegistry):
        self.api = api
        self.exchange = api.exchange
        self.registry = registry
        self.last_values: dict[str, float] = {}

    def _set_group(self, state: Any, handles: list[ScheduleHandle], value: float | None) -> None:
        if value is None:
            return
        for schedule in handles:
            self.exchange.set_actuator_value(state, schedule.actuator_handle, float(value))
            self.last_values[schedule.name] = float(value)

    def _reset_group(self, state: Any, handles: list[ScheduleHandle]) -> None:
        for schedule in handles:
            self.exchange.reset_actuator(state, schedule.actuator_handle)
            self.last_values.pop(schedule.name, None)

    def reset_all(self, state: Any) -> None:
        self._reset_group(state, self.registry.cooling_schedules)
        self._reset_group(state, self.registry.heating_schedules)
        self._reset_group(state, self.registry.lighting_schedules)
        self._reset_group(state, self.registry.ventilation_schedules)

    def apply(self, state: Any, action: ControlAction, total_occupants: float) -> dict[str, Any]:
        if action.reset_to_baseline:
            self.reset_all(state)
            return {"reset_to_baseline": True, "applied_values": {}}

        if total_occupants <= 0.1 and not action.force_when_unoccupied:
            self.reset_all(state)
            return {
                "reset_to_baseline": True,
                "reason": "No occupancy was detected and the action was not authorized for unoccupied control.",
                "applied_values": {},
            }

        self._set_group(state, self.registry.cooling_schedules, action.cooling_setpoint_c)
        self._set_group(state, self.registry.heating_schedules, action.heating_setpoint_c)
        self._set_group(state, self.registry.lighting_schedules, action.lighting_fraction)
        self._set_group(state, self.registry.ventilation_schedules, action.ventilation_fraction)
        return {
            "reset_to_baseline": False,
            "applied_values": dict(self.last_values),
            "actuator_counts": {
                "cooling": len(self.registry.cooling_schedules),
                "heating": len(self.registry.heating_schedules),
                "lighting": len(self.registry.lighting_schedules),
                "ventilation": len(self.registry.ventilation_schedules),
            },
        }
