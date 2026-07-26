from __future__ import annotations

from dataclasses import dataclass

from agent.schemas import BuildingState, ControlAction
from core.config import settings


@dataclass(frozen=True)
class ConstraintConfig:
    occupied_temp_min_c: float = settings.occupied_temp_min_c
    occupied_temp_max_c: float = settings.occupied_temp_max_c
    max_abs_pmv: float = settings.max_abs_pmv
    max_co2_ppm: float = settings.max_co2_ppm
    min_heating_setpoint_c: float = settings.min_heating_setpoint_c
    max_heating_setpoint_c: float = settings.max_heating_setpoint_c
    min_cooling_setpoint_c: float = settings.min_cooling_setpoint_c
    max_cooling_setpoint_c: float = settings.max_cooling_setpoint_c
    min_deadband_c: float = settings.min_deadband_c
    minimum_confidence: float = 0.50


class ConstraintChecker:
    def __init__(self, config: ConstraintConfig | None = None):
        self.config = config or ConstraintConfig()

    def validate(self, action: ControlAction, state: BuildingState) -> tuple[list[str], list[str]]:
        errors: list[str] = []
        warnings: list[str] = []
        cfg = self.config

        if action.reset_to_baseline:
            return errors, warnings

        has_control = any(
            value is not None
            for value in (
                action.cooling_setpoint_c,
                action.heating_setpoint_c,
                action.lighting_fraction,
                action.ventilation_fraction,
            )
        )
        if not has_control:
            errors.append("The action contains no control value and is not a reset action.")

        if action.confidence < cfg.minimum_confidence:
            errors.append(f"Action confidence must be at least {cfg.minimum_confidence:.2f}.")

        if action.cooling_setpoint_c is not None and not (
            cfg.min_cooling_setpoint_c <= action.cooling_setpoint_c <= cfg.max_cooling_setpoint_c
        ):
            errors.append(
                f"Cooling setpoint must be between {cfg.min_cooling_setpoint_c:.1f} and "
                f"{cfg.max_cooling_setpoint_c:.1f} °C."
            )

        if action.heating_setpoint_c is not None and not (
            cfg.min_heating_setpoint_c <= action.heating_setpoint_c <= cfg.max_heating_setpoint_c
        ):
            errors.append(
                f"Heating setpoint must be between {cfg.min_heating_setpoint_c:.1f} and "
                f"{cfg.max_heating_setpoint_c:.1f} °C."
            )

        if action.cooling_setpoint_c is not None and action.heating_setpoint_c is not None:
            if action.cooling_setpoint_c - action.heating_setpoint_c < cfg.min_deadband_c:
                errors.append(
                    f"Heating and cooling setpoints require at least a {cfg.min_deadband_c:.1f} °C deadband."
                )

        occupied_zones = [zone for zone in state.zones if zone.occupied]
        if not occupied_zones and action.force_when_unoccupied and action.mode != "PRECOOL":
            errors.append("Forced unoccupied control is only allowed in PRECOOL mode.")

        high_temperature = [
            zone for zone in occupied_zones
            if zone.temperature_c is not None and zone.temperature_c >= cfg.occupied_temp_max_c - 0.3
        ]
        high_pmv = [
            zone for zone in occupied_zones
            if zone.pmv is not None and zone.pmv >= cfg.max_abs_pmv - 0.1
        ]
        if (high_temperature or high_pmv) and action.cooling_setpoint_c is not None:
            if action.cooling_setpoint_c > 25.0:
                errors.append(
                    "Cooling setpoint above 25 °C is unsafe because an occupied zone is near its comfort limit."
                )

        low_temperature = [
            zone for zone in occupied_zones
            if zone.temperature_c is not None and zone.temperature_c <= cfg.occupied_temp_min_c + 0.3
        ]
        low_pmv = [
            zone for zone in occupied_zones
            if zone.pmv is not None and zone.pmv <= -cfg.max_abs_pmv + 0.1
        ]
        if (low_temperature or low_pmv) and action.heating_setpoint_c is not None:
            if action.heating_setpoint_c < 20.5:
                errors.append(
                    "Heating setpoint below 20.5 °C is unsafe because an occupied zone is near its comfort limit."
                )

        high_co2 = [
            zone for zone in occupied_zones
            if zone.co2_ppm is not None and zone.co2_ppm >= cfg.max_co2_ppm - 100
        ]
        if high_co2 and action.ventilation_fraction is not None and action.ventilation_fraction < 1.0:
            errors.append("Ventilation cannot be reduced while occupied-zone CO₂ is near its limit.")

        if action.lighting_fraction is not None and occupied_zones and action.lighting_fraction < 0.5:
            warnings.append("Lighting below 50% may affect visual comfort; verify daylight availability.")

        if action.ventilation_fraction is not None and action.ventilation_fraction < 0.6:
            warnings.append("Very low ventilation requires validated CO₂ sensing and an IAQ recovery path.")

        return errors, warnings
