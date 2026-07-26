from agent.schemas import BuildingState, ControlAction, ZoneState
from control.safety_shield import SafetyShield


def build_state(step: int = 4) -> BuildingState:
    return BuildingState(
        run_id="test",
        mode="controlled",
        sim_step=step,
        sim_time_hours=1.0,
        timestamp_utc="2026-01-01T00:00:00+00:00",
        zones=[ZoneState(name="Zone", temperature_c=24.0, occupants=2, occupied=True)],
        total_occupants=2,
    )


def test_token_is_bound_to_action():
    shield = SafetyShield()
    action = ControlAction(cooling_setpoint_c=25.0, reason="Test action", confidence=0.9)
    result = shield.validate(action, build_state())
    assert result.approved and result.approval_token
    valid, _ = shield.tokens.verify(result.approval_token, action, 4)
    assert valid
    changed = action.model_copy(update={"cooling_setpoint_c": 26.0})
    valid, _ = shield.tokens.verify(result.approval_token, changed, 4)
    assert not valid


def test_expired_token_is_rejected():
    shield = SafetyShield()
    action = ControlAction(cooling_setpoint_c=25.0, reason="Test action", confidence=0.9)
    result = shield.validate(action, build_state(step=4))
    valid, _ = shield.tokens.verify(result.approval_token, action, 100)
    assert not valid
