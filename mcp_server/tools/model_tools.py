from __future__ import annotations

from pathlib import Path
from typing import Any

from core.config import settings
from core.utils import read_json
from energyplus.idf_parser import inspect_idf


def inspect_building_model(idf_path: str | None = None) -> dict[str, Any]:
    """Parse an IDF and return zones, thermostat schedules, lights, and candidate actuators."""
    path = Path(idf_path).expanduser() if idf_path else settings.controlled_idf
    if not path.is_absolute():
        path = settings.project_root / path
    if not path.exists():
        return {"ok": False, "error": f"IDF file not found: {path}"}
    info = inspect_idf(path)
    return {"ok": True, "model": info.to_dict()}


def discover_exchange_points(filter_text: str = "", limit: int = 250) -> dict[str, Any]:
    """Return EnergyPlus exchange points discovered by the active controlled simulation."""
    data = read_json(settings.exchange_points_path, default=None)
    if not data:
        return {
            "ok": False,
            "error": "No exchange-point registry exists yet. Start the controlled EnergyPlus simulation first.",
        }
    points = data.get("exchange_points", [])
    if filter_text:
        needle = filter_text.lower()
        points = [
            point
            for point in points
            if needle in " ".join(str(value) for value in point.values()).lower()
        ]
    return {
        "ok": True,
        "selected_actuators": data.get("selected_actuators", {}),
        "count": min(len(points), max(1, limit)),
        "exchange_points": points[: max(1, min(limit, 1000))],
    }
