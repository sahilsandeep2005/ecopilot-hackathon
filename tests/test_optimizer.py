from agent.schemas import BuildingState, ZoneState
from control.optimizer import ControlOptimizer


def test_optimizer_returns_candidate():
    state = BuildingState(
        run_id="test",
        mode="controlled",
        sim_step=20,
        sim_time_hours=5.0,
        timestamp_utc="2026-01-01T00:00:00+00:00",
        calendar={"hour": 10},
        outdoor_temperature_c=30,
        facility_kw=80,
        peak_kw=90,
        total_occupants=10,
        zones=[
            ZoneState(
                name="Zone 1",
                temperature_c=24,
                pmv=0.2,
                co2_ppm=750,
                occupants=10,
                occupied=True,
            )
        ],
    )
    result = ControlOptimizer().optimize(state)
    assert result.selected_action.reason
    assert result.candidates
    assert result.candidates[0].total_score <= result.candidates[-1].total_score
