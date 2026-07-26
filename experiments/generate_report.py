from __future__ import annotations

import argparse
from pathlib import Path

from core.config import settings
from core.storage import SQLiteStore
from experiments.compare_runs import calculate_metrics


def create_markdown_report(output: Path, store: SQLiteStore | None = None) -> Path:
    store = store or SQLiteStore(settings.db_path)
    metrics = calculate_metrics(store)
    actions = store.actions(limit=100)
    events = store.events(limit=30)

    lines = [
        "# EcoPilot Experiment Report",
        "",
        "## Executive results",
        "",
        "| Metric | Result |",
        "|---|---:|",
        f"| Baseline electricity | {metrics['baseline_energy_kwh']:.3f} kWh |",
        f"| EcoPilot electricity | {metrics['controlled_energy_kwh']:.3f} kWh |",
        f"| Energy saving | {metrics['energy_saving_pct']:.2f}% |",
        f"| Baseline peak | {metrics['baseline_peak_kw']:.3f} kW |",
        f"| EcoPilot peak | {metrics['controlled_peak_kw']:.3f} kW |",
        f"| Peak reduction | {metrics['peak_reduction_pct']:.2f}% |",
        f"| Comfort compliance | {metrics['comfort_compliance_pct']:.2f}% |",
        f"| CO₂ compliance | {metrics['co2_compliance_pct']:.2f}% |",
        f"| Applied actions | {metrics['applied_actions']} |",
        f"| Rejected unsafe actions | {metrics['rejected_actions']} |",
        "",
        "## Method",
        "",
        "The baseline and controlled twins use identical IDF geometry, weather, occupancy, and simulation timesteps. "
        "The controlled twin receives only safety-approved schedule actuator overrides. Energy, demand, temperature, "
        "PMV, occupancy, and CO₂ are read through the EnergyPlus Runtime and Data Transfer APIs.",
        "",
        "## Control audit trail",
        "",
    ]
    if actions:
        lines.extend(["| Status | Mode | Step | Source | Reason |", "|---|---|---:|---|---|"])
        for row in reversed(actions):
            payload = row.get("payload", {})
            reason = str(payload.get("reason", "")).replace("|", "\\|")
            lines.append(
                f"| {row.get('status')} | {payload.get('mode')} | {payload.get('created_for_step')} | "
                f"{payload.get('source')} | {reason} |"
            )
    else:
        lines.append("No actions were recorded.")

    lines.extend(["", "## Recent warnings and errors", ""])
    important = [event for event in events if event.get("severity") in {"WARNING", "ERROR", "CRITICAL"}]
    if important:
        for event in important:
            lines.append(
                f"- **{event.get('severity')} — {event.get('source')}:** {event.get('message')}"
            )
    else:
        lines.append("No recent warning, error, or critical events were recorded.")

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the EcoPilot Markdown report.")
    parser.add_argument(
        "--output",
        type=Path,
        default=settings.project_root / "data" / "ecopilot-report.md",
    )
    args = parser.parse_args()
    output = create_markdown_report(args.output)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
