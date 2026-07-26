from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


COLORS = {
    "baseline": "#94a3b8",
    "controlled": "#38bdf8",
    "teal": "#2dd4bf",
    "green": "#4ade80",
    "amber": "#fbbf24",
    "red": "#fb7185",
    "purple": "#a78bfa",
    "grid": "rgba(148, 163, 184, 0.10)",
    "muted": "#7f91a8",
    "text": "#e2e8f0",
}


def states_to_frame(states: list[dict[str, Any]]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for state in states:
        rows.append(
            {
                "mode": state.get("mode"),
                "sim_step": state.get("sim_step"),
                "sim_time_hours": state.get("sim_time_hours"),
                "facility_kw": state.get("facility_kw"),
                "cumulative_kwh": state.get("cumulative_kwh"),
                "peak_kw": state.get("peak_kw"),
                "hvac_kwh": state.get("hvac_kwh"),
                "outdoor_temperature_c": state.get("outdoor_temperature_c"),
                "outdoor_relative_humidity_pct": state.get("outdoor_relative_humidity_pct"),
                "total_occupants": state.get("total_occupants"),
            }
        )
    return pd.DataFrame(rows)


def zones_to_frame(states: list[dict[str, Any]]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for state in states:
        for zone in state.get("zones", []):
            rows.append(
                {
                    "sim_step": state.get("sim_step"),
                    "sim_time_hours": state.get("sim_time_hours"),
                    "zone": zone.get("name"),
                    "temperature_c": zone.get("temperature_c"),
                    "relative_humidity_pct": zone.get("relative_humidity_pct"),
                    "pmv": zone.get("pmv"),
                    "co2_ppm": zone.get("co2_ppm"),
                    "occupants": zone.get("occupants"),
                    "occupied": zone.get("occupied"),
                    "cooling_setpoint_c": zone.get("cooling_setpoint_c"),
                    "heating_setpoint_c": zone.get("heating_setpoint_c"),
                }
            )
    return pd.DataFrame(rows)


def _base_layout(figure: go.Figure, *, height: int = 360, y_title: str = "") -> go.Figure:
    figure.update_layout(
        height=height,
        margin=dict(l=16, r=16, t=22, b=16),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(6,16,29,0.22)",
        font=dict(family="Inter, sans-serif", color=COLORS["text"], size=12),
        hovermode="x unified",
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            bgcolor="rgba(0,0,0,0)",
            font=dict(color="#a5b4c7", size=11),
        ),
        xaxis=dict(
            title="Simulation time (h)",
            showgrid=True,
            gridcolor=COLORS["grid"],
            zeroline=False,
            color=COLORS["muted"],
            fixedrange=True,
        ),
        yaxis=dict(
            title=y_title,
            showgrid=True,
            gridcolor=COLORS["grid"],
            zeroline=False,
            color=COLORS["muted"],
            fixedrange=True,
        ),
        hoverlabel=dict(bgcolor="#0f2034", bordercolor="rgba(148,163,184,.2)", font_color="#f8fafc"),
    )
    return figure


def _empty_figure(message: str, height: int = 360) -> go.Figure:
    figure = go.Figure()
    figure.add_annotation(
        text=message,
        x=0.5,
        y=0.5,
        xref="paper",
        yref="paper",
        showarrow=False,
        font=dict(color="#7f91a8", size=13),
    )
    figure.update_xaxes(visible=False)
    figure.update_yaxes(visible=False)
    return _base_layout(figure, height=height)


def energy_comparison_chart(baseline: pd.DataFrame, controlled: pd.DataFrame) -> go.Figure:
    if baseline.empty and controlled.empty:
        return _empty_figure("Waiting for energy telemetry")

    figure = go.Figure()
    if not baseline.empty:
        figure.add_trace(
            go.Scatter(
                x=baseline["sim_time_hours"],
                y=baseline["cumulative_kwh"],
                mode="lines",
                name="Baseline",
                line=dict(color=COLORS["baseline"], width=2),
                hovertemplate="%{y:.2f} kWh<extra>Baseline</extra>",
            )
        )
    if not controlled.empty:
        figure.add_trace(
            go.Scatter(
                x=controlled["sim_time_hours"],
                y=controlled["cumulative_kwh"],
                mode="lines",
                name="EcoPilot",
                fill="tozeroy",
                fillcolor="rgba(56,189,248,0.08)",
                line=dict(color=COLORS["controlled"], width=3),
                hovertemplate="%{y:.2f} kWh<extra>EcoPilot</extra>",
            )
        )
    return _base_layout(figure, y_title="Cumulative energy (kWh)")


def demand_comparison_chart(baseline: pd.DataFrame, controlled: pd.DataFrame) -> go.Figure:
    if baseline.empty and controlled.empty:
        return _empty_figure("Waiting for demand telemetry")

    figure = go.Figure()
    if not baseline.empty:
        figure.add_trace(
            go.Scatter(
                x=baseline["sim_time_hours"],
                y=baseline["facility_kw"],
                mode="lines",
                name="Baseline",
                line=dict(color=COLORS["baseline"], width=2),
                hovertemplate="%{y:.2f} kW<extra>Baseline</extra>",
            )
        )
    if not controlled.empty:
        figure.add_trace(
            go.Scatter(
                x=controlled["sim_time_hours"],
                y=controlled["facility_kw"],
                mode="lines",
                name="EcoPilot",
                line=dict(color=COLORS["teal"], width=3),
                hovertemplate="%{y:.2f} kW<extra>EcoPilot</extra>",
            )
        )
    return _base_layout(figure, y_title="Facility demand (kW)")


def zone_temperature_chart(zone_frame: pd.DataFrame, minimum: float, maximum: float) -> go.Figure:
    clean = zone_frame.dropna(subset=["temperature_c"]) if not zone_frame.empty else zone_frame
    if clean.empty:
        return _empty_figure("No zone temperature data available")

    figure = go.Figure()
    for zone, group in clean.groupby("zone", sort=False):
        figure.add_trace(
            go.Scatter(
                x=group["sim_time_hours"],
                y=group["temperature_c"],
                mode="lines",
                name=str(zone),
                line=dict(width=2.2),
                hovertemplate=f"{zone}<br>%{{y:.1f}} °C<extra></extra>",
            )
        )
    figure.add_hrect(
        y0=minimum,
        y1=maximum,
        fillcolor="rgba(74,222,128,0.07)",
        line_width=0,
        annotation_text="Comfort band",
        annotation_position="top left",
        annotation_font_color="#86efac",
    )
    figure.add_hline(y=minimum, line_dash="dot", line_color="rgba(74,222,128,.45)")
    figure.add_hline(y=maximum, line_dash="dot", line_color="rgba(74,222,128,.45)")
    return _base_layout(figure, y_title="Zone temperature (°C)")


def zone_co2_chart(zone_frame: pd.DataFrame, maximum: float) -> go.Figure:
    clean = zone_frame.dropna(subset=["co2_ppm"]) if not zone_frame.empty and "co2_ppm" in zone_frame else pd.DataFrame()
    if clean.empty:
        return _empty_figure("CO₂ telemetry is unavailable for this IDF")

    figure = go.Figure()
    for zone, group in clean.groupby("zone", sort=False):
        figure.add_trace(
            go.Scatter(
                x=group["sim_time_hours"],
                y=group["co2_ppm"],
                mode="lines",
                name=str(zone),
                line=dict(width=2.2),
                hovertemplate=f"{zone}<br>%{{y:.0f}} ppm<extra></extra>",
            )
        )
    figure.add_hrect(
        y0=0,
        y1=maximum,
        fillcolor="rgba(45,212,191,0.05)",
        line_width=0,
    )
    figure.add_hline(
        y=maximum,
        line_dash="dash",
        line_color=COLORS["amber"],
        annotation_text=f"IAQ limit · {maximum:.0f} ppm",
        annotation_position="top left",
        annotation_font_color="#fde68a",
    )
    return _base_layout(figure, y_title="CO₂ concentration (ppm)")


def operation_context_chart(controlled: pd.DataFrame) -> go.Figure:
    if controlled.empty:
        return _empty_figure("Waiting for environmental context")

    figure = make_subplots(specs=[[{"secondary_y": True}]])
    figure.add_trace(
        go.Scatter(
            x=controlled["sim_time_hours"],
            y=controlled["outdoor_temperature_c"],
            name="Outdoor temperature",
            mode="lines",
            line=dict(color=COLORS["amber"], width=2.4),
            hovertemplate="%{y:.1f} °C<extra>Outdoor</extra>",
        ),
        secondary_y=False,
    )
    figure.add_trace(
        go.Scatter(
            x=controlled["sim_time_hours"],
            y=controlled["total_occupants"],
            name="Occupancy",
            mode="lines",
            fill="tozeroy",
            fillcolor="rgba(167,139,250,.08)",
            line=dict(color=COLORS["purple"], width=2.2),
            hovertemplate="%{y:.0f}<extra>Occupants</extra>",
        ),
        secondary_y=True,
    )
    _base_layout(figure, y_title="Outdoor temperature (°C)")
    figure.update_yaxes(title_text="Occupants", secondary_y=True, showgrid=False, color=COLORS["muted"], fixedrange=True)
    return figure


def action_status_chart(actions: list[dict[str, Any]]) -> go.Figure:
    if not actions:
        return _empty_figure("No agent actions recorded", height=300)

    counts: dict[str, int] = {}
    for action in actions:
        status = str(action.get("status", "unknown")).title()
        counts[status] = counts.get(status, 0) + 1

    figure = go.Figure(
        go.Pie(
            labels=list(counts.keys()),
            values=list(counts.values()),
            hole=0.67,
            textinfo="label+value",
            textfont=dict(color="#dbeafe", size=11),
            marker=dict(colors=[COLORS["teal"], COLORS["controlled"], COLORS["amber"], COLORS["red"], COLORS["purple"]]),
            hovertemplate="%{label}: %{value}<extra></extra>",
        )
    )
    figure.add_annotation(text=f"<b>{sum(counts.values())}</b><br><span style='font-size:11px'>ACTIONS</span>", x=.5, y=.5, showarrow=False, font=dict(color="#f8fafc", size=18))
    figure.update_layout(showlegend=False)
    return _base_layout(figure, height=300)


def savings_gauge(value: float) -> go.Figure:
    display_value = max(-20.0, min(40.0, float(value)))
    figure = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=display_value,
            number={"suffix": "%", "font": {"color": "#f8fafc", "size": 34}},
            title={"text": "Measured energy saving", "font": {"color": "#94a3b8", "size": 12}},
            gauge={
                "axis": {"range": [-20, 40], "tickcolor": "#64748b", "tickfont": {"color": "#64748b"}},
                "bar": {"color": COLORS["teal"], "thickness": .28},
                "bgcolor": "rgba(6,16,29,.35)",
                "borderwidth": 0,
                "steps": [
                    {"range": [-20, 0], "color": "rgba(251,113,133,.12)"},
                    {"range": [0, 10], "color": "rgba(251,191,36,.10)"},
                    {"range": [10, 40], "color": "rgba(74,222,128,.10)"},
                ],
                "threshold": {"line": {"color": "#f8fafc", "width": 2}, "thickness": .72, "value": display_value},
            },
        )
    )
    figure.update_layout(showlegend=False)
    return _base_layout(figure, height=300)
