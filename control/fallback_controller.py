from __future__ import annotations

from agent.schemas import BuildingState, ControlAction
from core.config import settings


def safe_fallback_action(state: BuildingState, reason: str) -> ControlAction:
    occupied = [zone for zone in state.zones if zone.occupied]
    hot = any(
        zone.temperature_c is not None and zone.temperature_c > settings.occupied_temp_max_c - 0.5
        for zone in occupied
    )
    cold = any(
        zone.temperature_c is not None and zone.temperature_c < settings.occupied_temp_min_c + 0.5
        for zone in occupied
    )

    if hot:
        return ControlAction(
            mode="COMFORT_RECOVERY",
            cooling_setpoint_c=24.0,
            heating_setpoint_c=20.0,
            lighting_fraction=1.0,
            ventilation_fraction=1.0,
            hold_steps=2,
            reason=f"Safety fallback: {reason}. Occupied-zone heat risk detected.",
            confidence=1.0,
            created_for_step=state.sim_step,
            source="fallback_controller",
        )
    if cold:
        return ControlAction(
            mode="COMFORT_RECOVERY",
            cooling_setpoint_c=25.0,
            heating_setpoint_c=21.0,
            lighting_fraction=1.0,
            ventilation_fraction=1.0,
            hold_steps=2,
            reason=f"Safety fallback: {reason}. Occupied-zone cold risk detected.",
            confidence=1.0,
            created_for_step=state.sim_step,
            source="fallback_controller",
        )
    return ControlAction(
        mode="SAFE_FALLBACK",
        reset_to_baseline=True,
        hold_steps=1,
        reason=f"Safety fallback: {reason}. Restore the original EnergyPlus schedules.",
        confidence=1.0,
        created_for_step=state.sim_step,
        source="fallback_controller",
    )
