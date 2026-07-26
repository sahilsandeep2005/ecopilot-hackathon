from pathlib import Path

from core.storage import SQLiteStore


def test_state_and_action_roundtrip(tmp_path: Path):
    store = SQLiteStore(tmp_path / "test.db")
    state = {
        "run_id": "r1",
        "mode": "controlled",
        "sim_step": 1,
        "sim_time_hours": 0.25,
        "timestamp_utc": "2026-01-01T00:00:00+00:00",
        "facility_kw": 10,
        "cumulative_kwh": 2,
        "peak_kw": 10,
        "zones": [],
    }
    store.insert_state(state)
    assert store.latest_state("controlled")["sim_step"] == 1
    action = {
        "action_id": "a1",
        "created_for_step": 1,
        "source": "test",
        "mode": "NORMAL",
        "reason": "Test action",
    }
    row = store.insert_action(action, "token")
    assert row["payload"]["action_id"] == "a1"
    assert store.next_approved_action(0)["id"] == row["id"]
