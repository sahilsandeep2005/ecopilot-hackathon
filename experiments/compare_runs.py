from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from core.config import settings
from core.storage import SQLiteStore
from core.utils import write_json


def _compliance(states: list[dict[str, Any]]) -> tuple[float, float, int, int]:
    comfort_ok = 0
    comfort_total = 0
    co2_ok = 0
    co2_total = 0
    for state in states:
        for zone in state.get("zones", []):
            if not zone.get("occupied"):
                continue
            temperature = zone.get("temperature_c")
            pmv = zone.get("pmv")
            if temperature is not None:
                comfort_total += 1
                temperature_ok = settings.occupied_temp_min_c <= temperature <= settings.occupied_temp_max_c
                pmv_ok = pmv is None or abs(float(pmv)) <= settings.max_abs_pmv
                if temperature_ok and pmv_ok:
                    comfort_ok += 1
            co2 = zone.get("co2_ppm")
            if co2 is not None:
                co2_total += 1
                if float(co2) <= settings.max_co2_ppm:
                    co2_ok += 1
    comfort_pct = comfort_ok / comfort_total * 100.0 if comfort_total else 100.0
    co2_pct = co2_ok / co2_total * 100.0 if co2_total else 100.0
    return comfort_pct, co2_pct, comfort_ok, comfort_total


def calculate_metrics(store: SQLiteStore | None = None) -> dict[str, Any]:
    store = store or SQLiteStore(settings.db_path)
    baseline = store.all_states("baseline")
    controlled = store.all_states("controlled")
    latest_comparison = store.compare_latest()
    comfort_pct, co2_pct, comfort_ok, comfort_total = _compliance(controlled)
    actions = store.actions(limit=5000)
    applied = sum(1 for action in actions if action.get("status") in {"applied", "completed"})
    rejected = sum(1 for action in actions if action.get("status") == "rejected")

    return {
        "ready": bool(baseline and controlled),
        "baseline_state_count": len(baseline),
        "controlled_state_count": len(controlled),
        "baseline_energy_kwh": latest_comparison.get("baseline_cumulative_kwh", 0.0),
        "controlled_energy_kwh": latest_comparison.get("controlled_cumulative_kwh", 0.0),
        "energy_saving_pct": latest_comparison.get("energy_saving_pct", 0.0),
        "baseline_peak_kw": latest_comparison.get("baseline_peak_kw", 0.0),
        "controlled_peak_kw": latest_comparison.get("controlled_peak_kw", 0.0),
        "peak_reduction_pct": latest_comparison.get("peak_reduction_pct", 0.0),
        "comfort_compliance_pct": comfort_pct,
        "co2_compliance_pct": co2_pct,
        "comfort_compliant_observations": comfort_ok,
        "comfort_observations": comfort_total,
        "applied_actions": applied,
        "rejected_actions": rejected,
        "warning_events": len(store.events(limit=5000, severity="WARNING")),
        "error_events": len(store.events(limit=5000, severity="ERROR")),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare EcoPilot baseline and controlled runs.")
    parser.add_argument("--output", type=Path, default=settings.project_root / "data" / "metrics.json")
    args = parser.parse_args()
    metrics = calculate_metrics()
    write_json(args.output, metrics)
    print(json.dumps(metrics, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
