from __future__ import annotations

import time
from typing import Any

from agent.schemas import BuildingState, ControlAction
from control.safety_shield import SafetyShield
from core.storage import SQLiteStore
from energyplus.actuator_writer import ActuatorWriter
from energyplus.handle_registry import HandleRegistry
from energyplus.runtime_monitor import RuntimeMonitor
from energyplus.sensor_reader import SensorReader


class SimulationCallbacks:
    def __init__(
        self,
        api: Any,
        store: SQLiteStore,
        registry: HandleRegistry,
        reader: SensorReader,
        writer: ActuatorWriter,
        monitor: RuntimeMonitor,
        mode: str,
        realtime_delay: float = 0.0,
    ):
        self.api = api
        self.exchange = api.exchange
        self.store = store
        self.registry = registry
        self.reader = reader
        self.writer = writer
        self.monitor = monitor
        self.mode = mode
        self.realtime_delay = max(0.0, realtime_delay)
        self.safety = SafetyShield()
        self.sim_step = 0
        self.last_action_row_id = 0
        self.active_action: ControlAction | None = None
        self.active_action_row_id: int | None = None
        self.active_until_step = 0
        self.last_state: BuildingState | None = None
        self.applied_this_action = False

    def _ready(self, state: Any) -> bool:
        if not self.exchange.api_data_fully_ready(state):
            return False
        self.registry.initialize(state)
        return self.registry.initialized

    def _warmup(self, state: Any) -> bool:
        return bool(self.exchange.warmup_flag(state))

    def _load_next_action(self) -> None:
        row = self.store.next_approved_action(self.last_action_row_id)
        if not row:
            return
        self.last_action_row_id = int(row["id"])
        try:
            action = ControlAction.model_validate(row["payload"])
        except Exception as exc:
            self.store.mark_action(int(row["id"]), "rejected")
            self.store.log_event(
                "ERROR", "controlled_runner", f"Rejected malformed approved action: {exc}"
            )
            return

        if self.last_state is not None:
            validation = self.safety.validate(action, self.last_state, issue_token=False)
            if not validation.approved:
                self.store.mark_action(int(row["id"]), "rejected")
                self.store.log_event(
                    "WARNING",
                    "controlled_runner",
                    "Runtime safety recheck rejected an action.",
                    {"action": action.model_dump(mode="json"), "reasons": validation.reasons},
                )
                return

        self.active_action = action
        self.active_action_row_id = int(row["id"])
        self.active_until_step = self.sim_step + action.hold_steps
        self.applied_this_action = False

    def before_zone_timestep(self, state: Any) -> None:
        if not self._ready(state) or self._warmup(state):
            return
        if self.mode != "controlled":
            return

        self._load_next_action()
        if self.active_action is None:
            return

        total_occupants = self.last_state.total_occupants if self.last_state else 0.0
        details = self.writer.apply(state, self.active_action, total_occupants)
        if not self.applied_this_action and self.active_action_row_id is not None:
            self.store.mark_action(self.active_action_row_id, "applied", self.sim_step + 1)
            self.store.log_event(
                "INFO",
                "controlled_runner",
                f"Applied {self.active_action.mode} action.",
                {
                    "action": self.active_action.model_dump(mode="json"),
                    "runtime_application": details,
                },
            )
            self.applied_this_action = True

    def after_zone_timestep(self, state: Any) -> None:
        if not self._ready(state) or self._warmup(state):
            return
        self.sim_step += 1
        active_payload = self.active_action.model_dump(mode="json") if self.active_action else None
        building_state = self.reader.read(
            state,
            self.sim_step,
            active_payload,
            self.monitor.summary(),
        )
        self.last_state = building_state
        self.store.insert_state(building_state.model_dump(mode="json"))

        if self.active_action is not None and self.sim_step >= self.active_until_step:
            if self.mode == "controlled":
                self.writer.reset_all(state)
            if self.active_action_row_id is not None:
                self.store.mark_action(self.active_action_row_id, "completed", self.sim_step)
            self.active_action = None
            self.active_action_row_id = None
            self.applied_this_action = False

        if self.realtime_delay > 0:
            time.sleep(self.realtime_delay)
