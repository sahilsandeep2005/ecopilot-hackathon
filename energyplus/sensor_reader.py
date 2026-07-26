from __future__ import annotations

from typing import Any

from agent.schemas import BuildingState, ZoneState
from core.utils import utc_now_iso
from energyplus.handle_registry import HandleRegistry


class SensorReader:
    def __init__(self, api: Any, registry: HandleRegistry, run_id: str, mode: str):
        self.api = api
        self.exchange = api.exchange
        self.registry = registry
        self.run_id = run_id
        self.mode = mode
        self.cumulative_joules = 0.0
        self.hvac_cumulative_joules = 0.0
        self.peak_kw = 0.0

    def _variable(self, state: Any, handle: int) -> float | None:
        if handle < 0:
            return None
        value = float(self.exchange.get_variable_value(state, handle))
        if self.exchange.api_error_flag(state):
            self.exchange.reset_api_error_flag(state)
            return None
        return value

    def _meter(self, state: Any, handle: int) -> float | None:
        if handle < 0:
            return None
        value = float(self.exchange.get_meter_value(state, handle))
        if self.exchange.api_error_flag(state):
            self.exchange.reset_api_error_flag(state)
            return None
        return value

    def _zone_pmv(self, state: Any, zone_name: str) -> float | None:
        values: list[float] = []
        for people_name, people_zone in self.registry.model_info.people_to_zone.items():
            if people_zone.upper() != zone_name.upper():
                continue
            value = self._variable(state, self.registry.people_pmv_handles.get(people_name, -1))
            if value is not None:
                values.append(value)
        return sum(values) / len(values) if values else None

    def read(
        self,
        state: Any,
        sim_step: int,
        active_action: dict | None,
        runtime_summary: dict,
    ) -> BuildingState:
        zones: list[ZoneState] = []
        total_occupants = 0.0
        for zone_name, handles in self.registry.zone_handles.items():
            occupants = self._variable(state, handles.get("occupants", -1)) or 0.0
            total_occupants += occupants
            zones.append(
                ZoneState(
                    name=zone_name,
                    temperature_c=self._variable(state, handles.get("temperature_c", -1)),
                    relative_humidity_pct=self._variable(
                        state, handles.get("relative_humidity_pct", -1)
                    ),
                    pmv=self._zone_pmv(state, zone_name),
                    co2_ppm=self._variable(state, handles.get("co2_ppm", -1)),
                    occupants=occupants,
                    occupied=occupants > 0.1,
                    cooling_setpoint_c=self._variable(
                        state, handles.get("cooling_setpoint_c", -1)
                    ),
                    heating_setpoint_c=self._variable(
                        state, handles.get("heating_setpoint_c", -1)
                    ),
                )
            )

        dt_hours = 0.0

        zone_timestep = getattr(self.exchange, "zone_time_step", None)
        if zone_timestep is not None:
            dt_hours = float(zone_timestep(state))

        if dt_hours <= 0:
            steps_per_hour = max(
                1,
                int(self.exchange.num_time_steps_in_hour(state)),
            )
            dt_hours = 1.0 / steps_per_hour

        # Read instantaneous whole-building demand.
        demand_watts = self._variable(
            state,
            self.registry.facility_demand_handle,
        )

        # Read timestep energy from EnergyPlus meters.
        facility_joules = self._meter(
            state,
            self.registry.facility_meter_handle,
        )

        hvac_joules = self._meter(
            state,
            self.registry.hvac_meter_handle,
        )

        # Some example IDFs do not return the facility meter correctly through
        # the Runtime API. In that case, integrate instantaneous demand.
        if facility_joules is None or facility_joules <= 0.0:
            facility_joules = (
                max(0.0, demand_watts or 0.0)
                * dt_hours
                * 3600.0
            )

        if hvac_joules is None:
            hvac_joules = 0.0

        self.cumulative_joules += max(0.0, facility_joules)
        self.hvac_cumulative_joules += max(0.0, hvac_joules)

        if demand_watts is not None:
            facility_kw = max(0.0, demand_watts / 1000.0)
        else:
            facility_kw = max(
                0.0,
                facility_joules / (dt_hours * 3_600_000.0),
            )

        self.peak_kw = max(self.peak_kw, facility_kw)

        return BuildingState(
            run_id=self.run_id,
            mode=self.mode,
            sim_step=sim_step,
            sim_time_hours=float(self.exchange.current_sim_time(state)),
            timestamp_utc=utc_now_iso(),
            calendar={
                "month": int(self.exchange.month(state)),
                "day": int(self.exchange.day_of_month(state)),
                "hour": int(self.exchange.hour(state)),
                "minute": int(self.exchange.minutes(state)),
                "day_of_week": int(self.exchange.day_of_week(state)),
            },
            outdoor_temperature_c=self._variable(
                state, self.registry.environment_handles.get("outdoor_temperature_c", -1)
            ),
            outdoor_relative_humidity_pct=self._variable(
                state,
                self.registry.environment_handles.get("outdoor_relative_humidity_pct", -1),
            ),
            facility_kw=facility_kw,
            cumulative_kwh=self.cumulative_joules / 3_600_000.0,
            peak_kw=self.peak_kw,
            hvac_kwh=self.hvac_cumulative_joules / 3_600_000.0,
            total_occupants=total_occupants,
            zones=zones,
            active_action=active_action,
            available_signals=self.registry.availability_summary(),
            runtime=runtime_summary,
        )
