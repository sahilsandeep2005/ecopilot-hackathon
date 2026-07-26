from __future__ import annotations

import json
from typing import Any

import pandas as pd
import streamlit as st

from core.config import settings
from core.storage import SQLiteStore
from dashboard.charts import (
    action_status_chart,
    demand_comparison_chart,
    energy_comparison_chart,
    operation_context_chart,
    savings_gauge,
    states_to_frame,
    zone_co2_chart,
    zone_temperature_chart,
    zones_to_frame,
)
from dashboard.theme import (
    inject_theme,
    render_action_card,
    render_hero,
    render_kpi,
    render_section,
    render_snapshot,
    render_zone_card,
)
from experiments.compare_runs import calculate_metrics


st.set_page_config(
    page_title="EcoPilot | Autonomous Building Intelligence",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={"About": "EcoPilot — Agentic EnergyPlus Digital Twin"},
)
inject_theme()

try:
    from streamlit_autorefresh import st_autorefresh

    st_autorefresh(interval=2000, key="ecopilot-refresh")
except ImportError:
    pass


PLOTLY_CONFIG = {
    "displayModeBar": False,
    "scrollZoom": False,
    "responsive": True,
}


def _fmt(value: Any, suffix: str = "", digits: int = 1, fallback: str = "N/A") -> str:
    if value is None:
        return fallback
    try:
        return f"{float(value):.{digits}f}{suffix}"
    except (TypeError, ValueError):
        return fallback


def _latest_zone_table(latest: dict[str, Any] | None) -> pd.DataFrame:
    if not latest:
        return pd.DataFrame()
    rows = []
    for zone in latest.get("zones", []):
        rows.append(
            {
                "Zone": zone.get("name"),
                "Occupancy": int(round(float(zone.get("occupants", 0) or 0))),
                "Temperature": _fmt(zone.get("temperature_c"), " °C"),
                "PMV": _fmt(zone.get("pmv"), digits=2),
                "CO₂": _fmt(zone.get("co2_ppm"), " ppm", digits=0),
                "Cooling SP": _fmt(zone.get("cooling_setpoint_c"), " °C"),
                "Heating SP": _fmt(zone.get("heating_setpoint_c"), " °C"),
            }
        )
    return pd.DataFrame(rows)


def _action_frame(actions: list[dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for row in actions:
        payload = row.get("payload", {}) or {}
        rows.append(
            {
                "Status": str(row.get("status", "unknown")).upper(),
                "Mode": payload.get("mode", "—"),
                "Decision step": payload.get("created_for_step", "—"),
                "Applied step": row.get("applied_step") or "—",
                "Confidence": _fmt((payload.get("confidence") or 0) * 100, "%", digits=0),
                "Source": payload.get("source", "—"),
                "Reason": payload.get("reason", "—"),
            }
        )
    return pd.DataFrame(rows)


def _event_frame(events: list[dict[str, Any]]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Time": event.get("created_at"),
                "Severity": event.get("severity"),
                "Source": event.get("source"),
                "Message": event.get("message"),
            }
            for event in events
        ]
    )


store = SQLiteStore(settings.db_path)
baseline_states = store.all_states("baseline")
controlled_states = store.all_states("controlled")
latest_baseline = store.latest_state("baseline")
latest_controlled = store.latest_state("controlled")
metrics = calculate_metrics(store)
comparison = store.compare_latest()
actions = store.actions(limit=200)
events = store.events(limit=100)

baseline_frame = states_to_frame(baseline_states)
controlled_frame = states_to_frame(controlled_states)
zone_frame = zones_to_frame(controlled_states)

is_live = bool(latest_controlled)
progress = float((latest_controlled or {}).get("runtime", {}).get("progress_pct", 0) or 0)
active_action = (latest_controlled or {}).get("active_action")
agent_mode = active_action.get("mode", "SAFE IDLE") if active_action else "SAFE IDLE"

saving = float(comparison.get("energy_saving_pct", 0.0) or 0.0) if comparison.get("ready") else 0.0
peak_reduction = float(comparison.get("peak_reduction_pct", 0.0) or 0.0) if comparison.get("ready") else 0.0
comfort = float(metrics.get("comfort_compliance_pct", 0.0) or 0.0)
co2_observed = bool(not zone_frame.empty and "co2_ppm" in zone_frame and zone_frame["co2_ppm"].notna().any())
co2_compliance = float(metrics.get("co2_compliance_pct", 0.0) or 0.0) if co2_observed else None
warning_count = int(metrics.get("warning_events", 0) or 0)
error_count = int(metrics.get("error_events", 0) or 0)

render_hero(live=is_live, progress=progress, mode=agent_mode)

if not baseline_states and not controlled_states:
    st.info(
        "No telemetry has arrived yet. Start the simulation in another terminal with "
        "`python -m experiments.run_scenarios --deterministic-agent --realtime-delay 0.25`."
    )

# Executive KPI strip
kpi_columns = st.columns(6)
with kpi_columns[0]:
    render_kpi(
        "Energy saving",
        f"{saving:+.1f}%",
        "Versus synchronized baseline",
        "⚡",
        "teal" if saving >= 0 else "red",
        "good" if saving >= 0 else "bad",
    )
with kpi_columns[1]:
    render_kpi(
        "Peak reduction",
        f"{peak_reduction:+.1f}%",
        "Maximum demand avoided",
        "↘",
        "cyan" if peak_reduction >= 0 else "red",
        "good" if peak_reduction >= 0 else "bad",
    )
with kpi_columns[2]:
    render_kpi(
        "Comfort compliance",
        f"{comfort:.1f}%",
        "Occupied-zone observations",
        "◒",
        "green" if comfort >= 95 else "amber",
        "good" if comfort >= 95 else "warn",
    )
with kpi_columns[3]:
    render_kpi(
        "IAQ compliance",
        "N/A" if co2_compliance is None else f"{co2_compliance:.1f}%",
        "CO₂ signal status",
        "◎",
        "purple" if co2_compliance is not None else "amber",
        "good" if co2_compliance is not None and co2_compliance >= 95 else "warn",
    )
with kpi_columns[4]:
    render_kpi(
        "Validated actions",
        str(int(metrics.get("applied_actions", 0) or 0)),
        f"{int(metrics.get('rejected_actions', 0) or 0)} unsafe rejected",
        "✦",
        "purple",
        "good",
    )
with kpi_columns[5]:
    render_kpi(
        "System health",
        "NOMINAL" if error_count == 0 else "ATTENTION",
        f"{warning_count} warnings · {error_count} errors",
        "●",
        "green" if error_count == 0 else "red",
        "good" if error_count == 0 else "bad",
    )

st.write("")
overview_tab, zones_tab, agent_tab, system_tab = st.tabs(
    ["◈ Command Overview", "▦ Zone Intelligence", "✦ Agent Decisions", "◉ System Health"]
)

with overview_tab:
    render_section(
        "Digital-twin performance",
        "Live comparison of the native EnergyPlus baseline and the safety-constrained EcoPilot twin.",
        "TWIN ANALYTICS",
    )
    chart_left, chart_right = st.columns(2)
    with chart_left:
        st.markdown('<div class="eco-card-title">Cumulative energy trajectory</div><div class="eco-card-subtitle">Lower EcoPilot trajectory indicates verified savings</div>', unsafe_allow_html=True)
        st.plotly_chart(
            energy_comparison_chart(baseline_frame, controlled_frame),
            use_container_width=True,
            config=PLOTLY_CONFIG,
            key="energy-overview",
        )
    with chart_right:
        st.markdown('<div class="eco-card-title">Facility demand profile</div><div class="eco-card-subtitle">Tracks instantaneous load and peak suppression</div>', unsafe_allow_html=True)
        st.plotly_chart(
            demand_comparison_chart(baseline_frame, controlled_frame),
            use_container_width=True,
            config=PLOTLY_CONFIG,
            key="demand-overview",
        )

    render_section(
        "Autonomous supervisory layer",
        "Every intervention is optimizer-generated, safety-validated, applied, and audited.",
        "AGENTIC CONTROL",
    )
    action_col, snapshot_col = st.columns([1.65, 1])
    with action_col:
        render_action_card(active_action)
        if active_action:
            with st.expander("Inspect complete action payload"):
                st.json(active_action)
    with snapshot_col:
        render_snapshot(latest_controlled)

    render_section(
        "Operating context",
        "Occupancy and outdoor conditions that explain changes in HVAC behavior.",
        "CONTEXT AWARENESS",
    )
    context_col, gauge_col = st.columns([1.7, 1])
    with context_col:
        st.plotly_chart(
            operation_context_chart(controlled_frame),
            use_container_width=True,
            config=PLOTLY_CONFIG,
            key="context-overview",
        )
    with gauge_col:
        st.plotly_chart(
            savings_gauge(saving),
            use_container_width=True,
            config=PLOTLY_CONFIG,
            key="saving-gauge",
        )

with zones_tab:
    render_section(
        "Live zone status",
        "At-a-glance comfort, occupancy, PMV and indoor-air-quality conditions.",
        "SPACE INTELLIGENCE",
    )
    latest_zones = (latest_controlled or {}).get("zones", [])
    if latest_zones:
        for start in range(0, min(len(latest_zones), 12), 4):
            row = st.columns(4)
            for column, zone in zip(row, latest_zones[start : start + 4]):
                with column:
                    render_zone_card(
                        zone,
                        settings.occupied_temp_min_c,
                        settings.occupied_temp_max_c,
                        settings.max_co2_ppm,
                    )
    else:
        st.info("Zone telemetry has not arrived yet.")

    render_section(
        "Comfort and indoor air quality",
        "Comfort bands and IAQ limits are shown directly on the live traces.",
        "CONSTRAINT MONITORING",
    )
    temp_col, co2_col = st.columns(2)
    with temp_col:
        st.markdown('<div class="eco-card-title">Zone temperature</div><div class="eco-card-subtitle">Occupied comfort band highlighted</div>', unsafe_allow_html=True)
        st.plotly_chart(
            zone_temperature_chart(
                zone_frame,
                settings.occupied_temp_min_c,
                settings.occupied_temp_max_c,
            ),
            use_container_width=True,
            config=PLOTLY_CONFIG,
            key="zone-temperature",
        )
    with co2_col:
        st.markdown('<div class="eco-card-title">Zone CO₂</div><div class="eco-card-subtitle">IAQ threshold and live concentration</div>', unsafe_allow_html=True)
        st.plotly_chart(
            zone_co2_chart(zone_frame, settings.max_co2_ppm),
            use_container_width=True,
            config=PLOTLY_CONFIG,
            key="zone-co2",
        )
        if not co2_observed:
            st.caption("Enable `ZoneAirContaminantBalance` in the IDF to populate this panel.")

    render_section(
        "Latest zone telemetry",
        "Current setpoints and measured conditions for evaluator inspection.",
        "AUDITABLE DATA",
    )
    zone_table = _latest_zone_table(latest_controlled)
    if not zone_table.empty:
        st.dataframe(zone_table, use_container_width=True, hide_index=True)
    else:
        st.info("No zone records are available.")

with agent_tab:
    render_section(
        "Decision intelligence",
        "Current strategy, validation status and complete action history.",
        "EXPLAINABLE AUTONOMY",
    )
    decision_col, distribution_col = st.columns([1.65, 1])
    with decision_col:
        render_action_card(active_action)
        if active_action:
            st.markdown("#### Actuator targets")
            targets = {
                "Cooling setpoint": _fmt(active_action.get("cooling_setpoint_c"), " °C"),
                "Heating setpoint": _fmt(active_action.get("heating_setpoint_c"), " °C"),
                "Lighting fraction": _fmt(active_action.get("lighting_fraction"), digits=2),
                "Ventilation fraction": _fmt(active_action.get("ventilation_fraction"), digits=2),
            }
            target_cols = st.columns(4)
            for column, (label, value) in zip(target_cols, targets.items()):
                column.metric(label, value)
    with distribution_col:
        st.plotly_chart(
            action_status_chart(actions),
            use_container_width=True,
            config=PLOTLY_CONFIG,
            key="action-status",
        )

    render_section(
        "Action audit trail",
        "Every proposal, rejection, application and completion is retained for traceability.",
        "CONTROL GOVERNANCE",
    )
    action_frame = _action_frame(actions)
    if not action_frame.empty:
        status_filter = st.multiselect(
            "Filter by status",
            options=sorted(action_frame["Status"].dropna().unique().tolist()),
            default=[],
            placeholder="Show all statuses",
        )
        filtered = action_frame[action_frame["Status"].isin(status_filter)] if status_filter else action_frame
        st.dataframe(filtered, use_container_width=True, hide_index=True)
    else:
        st.info("No actions have been recorded yet.")

with system_tab:
    render_section(
        "Runtime health",
        "Simulation progress, data pipeline state and integration endpoints.",
        "OPERATIONS",
    )
    health_left, health_right = st.columns([1, 1.5])
    with health_left:
        st.markdown(
            f"""
            <div class="eco-card">
                <div class="eco-card-title">Integration status</div>
                <div class="eco-card-subtitle">Live connectivity and telemetry indicators</div>
                <div style="margin-top:.8rem">
                    <div class="eco-health-row"><span class="eco-health-label">Baseline twin</span><span class="eco-health-value">{len(baseline_states)} states</span></div>
                    <div class="eco-health-row"><span class="eco-health-label">Controlled twin</span><span class="eco-health-value">{len(controlled_states)} states</span></div>
                    <div class="eco-health-row"><span class="eco-health-label">Simulation progress</span><span class="eco-health-value">{progress:.0f}%</span></div>
                    <div class="eco-health-row"><span class="eco-health-label">MCP endpoint</span><span class="eco-health-value">Configured</span></div>
                    <div class="eco-health-row"><span class="eco-health-label">LLM model</span><span class="eco-health-value">{settings.ollama_model}</span></div>
                    <div class="eco-health-row"><span class="eco-health-label">Safety errors</span><span class="eco-health-value">{error_count}</span></div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.write("")
        st.progress(min(max(progress / 100.0, 0.0), 1.0), text=f"EnergyPlus run {progress:.0f}% complete")
    with health_right:
        render_snapshot(latest_controlled)
       


with st.expander("⚙️ System configuration", expanded=False):

    st.caption(
        "Runtime configuration and safety boundaries used by the "
        "EcoPilot autonomous control system."
    )

    row1 = st.columns(3)

    row1[0].metric(
        label="AI supervisor",
        value=settings.ollama_model,
        help="Open-source LLM used for supervisory reasoning",
    )

    row1[1].metric(
        label="Agent protocol",
        value="MCP",
        help="Model Context Protocol tool-calling layer",
    )

    row1[2].metric(
        label="Data storage",
        value="SQLite • Ready",
        help="Local telemetry and audit database",
    )

    st.markdown("---")

    row2 = st.columns(3)

    row2[0].metric(
        label="Comfort range",
        value=(
            f"{settings.occupied_temp_min_c:.0f}–"
            f"{settings.occupied_temp_max_c:.0f} °C"
        ),
        help="Permitted occupied-zone temperature range",
    )

    row2[1].metric(
        label="Indoor air-quality limit",
        value=f"≤ {settings.max_co2_ppm:.0f} ppm",
        help="Maximum permitted zone CO₂ concentration",
    )

    row2[2].metric(
        label="Thermal comfort limit",
        value=f"±{settings.max_abs_pmv:.1f} PMV",
        help="Maximum permitted absolute Predicted Mean Vote",
    )

    st.markdown(
        """
        <div style="
            margin-top: 1rem;
            padding: 0.85rem 1rem;
            border: 1px solid rgba(51, 211, 153, 0.25);
            border-radius: 12px;
            background: rgba(16, 185, 129, 0.07);
            display: flex;
            align-items: center;
            gap: 10px;
        ">
        </div>
        """,
        unsafe_allow_html=True,
    )

    render_section(
        "System event stream",
        "OBSERVABILITY",
    )
    event_frame = _event_frame(events)
    if not event_frame.empty:
        severity_options = sorted(event_frame["Severity"].dropna().unique().tolist())
        selected_severity = st.multiselect(
            "Filter severity",
            options=severity_options,
            default=[],
            placeholder="Show all events",
        )
        filtered_events = (
            event_frame[event_frame["Severity"].isin(selected_severity)]
            if selected_severity
            else event_frame
        )
        st.dataframe(filtered_events, use_container_width=True, hide_index=True)
    else:
        st.success("No runtime events have been emitted.")

with st.sidebar:
    st.markdown("### ⚡ EcoPilot")
    st.caption("Autonomous Building Intelligence")
    st.divider()

    st.markdown("#### Live status")
    st.write("🟢 Controlled twin online" if latest_controlled else "🔴 Controlled twin waiting")
    st.write("🟢 Baseline twin online" if latest_baseline else "🔴 Baseline twin waiting")
    st.write(f"🧠 Agent mode: **{agent_mode}**")
    st.write(f"⏱️ Simulation step: **{(latest_controlled or {}).get('sim_step', '—')}**")

    st.divider()
    st.markdown("#### Demo controls")
    auto_refresh = st.toggle("Live refresh", value=True, disabled=True, help="Dashboard refresh is currently fixed at two seconds.")
    st.slider("Visible history", 25, 500, min(max(len(controlled_states), 25), 500), disabled=True)

    st.divider()
    st.markdown("#### Safety envelope")
    st.caption(f"Temperature: {settings.occupied_temp_min_c:.0f}–{settings.occupied_temp_max_c:.0f} °C")
    st.caption(f"PMV: ±{settings.max_abs_pmv:.1f}")
    st.caption(f"CO₂: ≤ {settings.max_co2_ppm:.0f} ppm")

    st.divider()
    st.caption(f"Database: {settings.db_path.name}")
    st.caption(f"Model: {settings.ollama_model}")

st.markdown(
    "<div class='eco-footer'>EcoPilot · Safety-constrained agentic control · Baseline and AI twin evaluated under identical conditions</div>",
    unsafe_allow_html=True,
)
