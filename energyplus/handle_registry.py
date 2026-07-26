from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.config import settings
from core.utils import write_json
from energyplus.idf_parser import IDFModelInfo


@dataclass
class ScheduleHandle:
    name: str
    component_type: str
    actuator_handle: int
    value_handle: int


class HandleRegistry:
    ZONE_VARIABLES = {
        "temperature_c": "Zone Mean Air Temperature",
        "relative_humidity_pct": "Zone Air Relative Humidity",
        "occupants": "Zone People Occupant Count",
        "co2_ppm": "Zone Air CO2 Concentration",
        "cooling_setpoint_c": "Zone Thermostat Cooling Setpoint Temperature",
        "heating_setpoint_c": "Zone Thermostat Heating Setpoint Temperature",
    }

    def __init__(self, api: Any, model_info: IDFModelInfo, mode: str):
        self.api = api
        self.exchange = api.exchange
        self.model_info = model_info
        self.mode = mode
        self.initialized = False
        self.zone_handles: dict[str, dict[str, int]] = {}
        self.people_pmv_handles: dict[str, int] = {}
        self.environment_handles: dict[str, int] = {}
        self.facility_demand_handle: int = -1
        self.facility_meter_handle: int = -1
        self.hvac_meter_handle: int = -1
        self.cooling_schedules: list[ScheduleHandle] = []
        self.heating_schedules: list[ScheduleHandle] = []
        self.lighting_schedules: list[ScheduleHandle] = []
        self.ventilation_schedules: list[ScheduleHandle] = []

    def request_variables(self, state: Any) -> None:
        for zone in self.model_info.zones:
            for variable_name in self.ZONE_VARIABLES.values():
                self.exchange.request_variable(state, variable_name, zone)
        for people_name in self.model_info.people_to_zone:
            self.exchange.request_variable(state, "Zone Thermal Comfort Fanger Model PMV", people_name)
        self.exchange.request_variable(state, "Site Outdoor Air Drybulb Temperature", "Environment")
        self.exchange.request_variable(state, "Site Outdoor Air Relative Humidity", "Environment")
        self.exchange.request_variable(state, "Facility Total Electricity Demand Rate", "Whole Building")
        for schedule_name in self._all_control_schedules():
            self.exchange.request_variable(state, "Schedule Value", schedule_name)

    def _all_control_schedules(self) -> set[str]:
        return set().union(
            self.model_info.cooling_schedules,
            self.model_info.heating_schedules,
            self.model_info.lighting_schedules,
            self.model_info.ventilation_schedules,
        )

    def _variable_handle(self, state: Any, variable_name: str, key: str) -> int:
        return int(self.exchange.get_variable_handle(state, variable_name, key))

    def _schedule_handles(
        self,
        state: Any,
        schedules: dict[str, str],
        available_points: list[Any],
    ) -> list[ScheduleHandle]:
        result: list[ScheduleHandle] = []
        for schedule_name, component_type in schedules.items():
            actuator_handle = int(
                self.exchange.get_actuator_handle(state, component_type, "Schedule Value", schedule_name)
            )
            if actuator_handle < 0:
                for point in available_points:
                    if (
                        str(getattr(point, "what", "")).lower() == "actuator"
                        and str(getattr(point, "key", "")).upper() == schedule_name.upper()
                        and str(getattr(point, "type", "")).upper() == "SCHEDULE VALUE"
                    ):
                        component_type = str(getattr(point, "name", component_type))
                        actuator_handle = int(
                            self.exchange.get_actuator_handle(
                                state, component_type, "Schedule Value", schedule_name
                            )
                        )
                        break
            value_handle = self._variable_handle(state, "Schedule Value", schedule_name)
            if actuator_handle >= 0:
                result.append(
                    ScheduleHandle(
                        name=schedule_name,
                        component_type=component_type,
                        actuator_handle=actuator_handle,
                        value_handle=value_handle,
                    )
                )
        return result

    def initialize(self, state: Any) -> None:
        if self.initialized or not self.exchange.api_data_fully_ready(state):
            return

        for zone in self.model_info.zones:
            self.zone_handles[zone] = {
                alias: self._variable_handle(state, variable_name, zone)
                for alias, variable_name in self.ZONE_VARIABLES.items()
            }
        for people_name in self.model_info.people_to_zone:
            self.people_pmv_handles[people_name] = self._variable_handle(
                state, "Zone Thermal Comfort Fanger Model PMV", people_name
            )

        self.environment_handles = {
            "outdoor_temperature_c": self._variable_handle(
                state, "Site Outdoor Air Drybulb Temperature", "Environment"
            ),
            "outdoor_relative_humidity_pct": self._variable_handle(
                state, "Site Outdoor Air Relative Humidity", "Environment"
            ),
        }
        self.facility_demand_handle = self._variable_handle(
            state, "Facility Total Electricity Demand Rate", "Whole Building"
        )
        self.facility_meter_handle = int(self.exchange.get_meter_handle(state, "Electricity:Facility"))
        self.hvac_meter_handle = int(self.exchange.get_meter_handle(state, "Electricity:HVAC"))

        available_points = list(self.exchange.get_api_data(state))
        self.cooling_schedules = self._schedule_handles(
            state, self.model_info.cooling_schedules, available_points
        )
        self.heating_schedules = self._schedule_handles(
            state, self.model_info.heating_schedules, available_points
        )
        self.lighting_schedules = self._schedule_handles(
            state, self.model_info.lighting_schedules, available_points
        )
        self.ventilation_schedules = self._schedule_handles(
            state, self.model_info.ventilation_schedules, available_points
        )

        exchange_points = []
        for point in available_points:
            exchange_points.append(
                {
                    "what": str(getattr(point, "what", "")),
                    "name": str(getattr(point, "name", "")),
                    "key": str(getattr(point, "key", "")),
                    "type": str(getattr(point, "type", "")),
                    "unit": str(getattr(point, "unit", "")),
                }
            )
        payload = {
            "mode": self.mode,
            "model": self.model_info.to_dict(),
            "selected_actuators": {
                "cooling": [handle.__dict__ for handle in self.cooling_schedules],
                "heating": [handle.__dict__ for handle in self.heating_schedules],
                "lighting": [handle.__dict__ for handle in self.lighting_schedules],
                "ventilation": [handle.__dict__ for handle in self.ventilation_schedules],
            },
            "exchange_points": exchange_points,
        }
        # Keep a per-twin registry so concurrent baseline and controlled processes cannot
        # overwrite each other's discovery data. MCP reads the canonical controlled file.
        write_json(settings.live_dir / f"exchange_points_{self.mode}.json", payload)
        if self.mode == "controlled":
            write_json(settings.exchange_points_path, payload)
        self.initialized = True

    def availability_summary(self) -> list[str]:
        signals: list[str] = []
        if any(handle >= 0 for handles in self.zone_handles.values() for handle in handles.values()):
            signals.append("zone_variables")
        if self.facility_meter_handle >= 0:
            signals.append("facility_electricity_meter")
        if self.facility_demand_handle >= 0:
            signals.append("facility_demand")
        if self.cooling_schedules:
            signals.append("cooling_schedule_actuators")
        if self.heating_schedules:
            signals.append("heating_schedule_actuators")
        if self.lighting_schedules:
            signals.append("lighting_schedule_actuators")
        if self.ventilation_schedules:
            signals.append("ventilation_schedule_actuators")
        return signals
