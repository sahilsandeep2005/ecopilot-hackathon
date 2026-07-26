from __future__ import annotations

from typing import Any

from core.config import settings
from core.storage import SQLiteStore

store = SQLiteStore(settings.db_path)


def get_live_building_state(mode: str = "controlled") -> dict[str, Any]:
    """Get the newest compact state published by an EnergyPlus twin."""
    if mode not in {"baseline", "controlled"}:
        return {"ok": False, "error": "mode must be baseline or controlled"}
    state = store.latest_state(mode)
    if state is None:
        return {"ok": False, "error": f"No {mode} state is available yet."}
    return {"ok": True, "state": state}


def get_recent_history(mode: str = "controlled", limit: int = 12) -> dict[str, Any]:
    """Get recent simulation states for trend reasoning without loading full EnergyPlus logs."""
    if mode not in {"baseline", "controlled"}:
        return {"ok": False, "error": "mode must be baseline or controlled"}
    states = store.recent_states(mode, limit=limit)
    return {"ok": bool(states), "mode": mode, "count": len(states), "states": states}


def compare_with_baseline() -> dict[str, Any]:
    """Compare current cumulative energy and peak demand between the two digital twins."""
    return store.compare_latest()
