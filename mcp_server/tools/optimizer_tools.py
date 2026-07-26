from __future__ import annotations

from typing import Any

from agent.schemas import BuildingState
from control.optimizer import ControlOptimizer
from core.config import settings
from core.storage import SQLiteStore

store = SQLiteStore(settings.db_path)
optimizer = ControlOptimizer(settings.project_root / "data" / "surrogate.joblib")


def optimize_control_action() -> dict[str, Any]:
    """Generate and rank safe control candidates for the newest controlled state."""
    raw_state = store.latest_state("controlled")
    if raw_state is None:
        return {"ok": False, "error": "No controlled building state is available."}
    state = BuildingState.model_validate(raw_state)
    result = optimizer.optimize(state)
    return {"ok": True, **result.model_dump(mode="json")}
