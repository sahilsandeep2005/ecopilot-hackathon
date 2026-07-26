from agent.schemas import BuildingState, ControlAction, ZoneState
from control.constraints import ConstraintChecker


def state(temp: float = 24.0, co2: float = 700.0) -> BuildingState:
    return BuildingState(
        run_id="test",
        mode="controlled",
        sim_step=10,
        sim_time_hours=2.5,
        timestamp_utc="2026-01-01T00:00:00+00:00",
        zones=[ZoneState(name="Zone 1", temperature_c=temp, co2_ppm=co2, occupants=5, occupied=True)],
        total_occupants=5,
    )


def test_valid_action_passes():
    action = ControlAction(
        mode="ECO",
        cooling_setpoint_c=25.0,
        heating_setpoint_c=20.0,
        lighting_fraction=0.8,
        ventilation_fraction=0.8,
        reason="Safe efficiency action",
        confidence=0.9,
        created_for_step=10,
    )
    errors, _ = ConstraintChecker().validate(action, state())
    assert errors == []


def test_deadband_is_enforced():
    action = ControlAction(
        cooling_setpoint_c=22.0,
        heating_setpoint_c=21.5,
        reason="Invalid deadband",
        confidence=0.9,
    )
    errors, _ = ConstraintChecker().validate(action, state())
    assert any("deadband" in error.lower() for error in errors)


def test_high_co2_blocks_ventilation_reduction():
    action = ControlAction(
        cooling_setpoint_c=24.5,
        ventilation_fraction=0.7,
        reason="Unsafe IAQ action",
        confidence=0.9,
    )
    errors, _ = ConstraintChecker().validate(action, state(co2=950.0))
    assert any("ventilation" in error.lower() for error in errors)
