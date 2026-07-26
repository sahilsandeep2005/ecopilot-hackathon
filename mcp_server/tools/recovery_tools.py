from __future__ import annotations

from typing import Any

from core.config import settings
from core.storage import SQLiteStore

store = SQLiteStore(settings.db_path)


def read_runtime_messages(limit: int = 30, severity: str = "") -> dict[str, Any]:
    """Read recent EnergyPlus, safety, agent, and orchestration events."""
    events = store.events(limit=limit, severity=severity or None)
    return {"ok": True, "count": len(events), "events": events}


def generate_final_report() -> dict[str, Any]:
    """Calculate headline energy, peak, comfort, and IAQ metrics from completed runs."""
    from experiments.compare_runs import calculate_metrics

    return calculate_metrics(store)
