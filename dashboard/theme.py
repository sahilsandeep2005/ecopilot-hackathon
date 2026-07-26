from __future__ import annotations

import html
from typing import Any

import streamlit as st


APP_CSS = r"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Space+Grotesk:wght@500;600;700&display=swap');

:root {
    --bg: #06101d;
    --panel: rgba(13, 27, 45, 0.72);
    --panel-strong: rgba(15, 32, 52, 0.94);
    --border: rgba(148, 163, 184, 0.16);
    --text: #f8fafc;
    --muted: #94a3b8;
    --cyan: #38bdf8;
    --teal: #2dd4bf;
    --green: #4ade80;
    --amber: #fbbf24;
    --red: #fb7185;
    --purple: #a78bfa;
}

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

.stApp {
    background:
        radial-gradient(circle at 15% -10%, rgba(56, 189, 248, 0.15), transparent 30%),
        radial-gradient(circle at 95% 5%, rgba(45, 212, 191, 0.12), transparent 25%),
        linear-gradient(180deg, #07111f 0%, #06101d 50%, #040b14 100%);
    color: var(--text);
}

[data-testid="stHeader"] {
    background: rgba(6, 16, 29, 0.72);
    backdrop-filter: blur(18px);
    border-bottom: 1px solid rgba(148, 163, 184, 0.08);
}

[data-testid="stToolbar"] { right: 1rem; }

.block-container {
    max-width: 1560px;
    padding-top: 1.2rem;
    padding-bottom: 4rem;
}

h1, h2, h3, h4 {
    font-family: 'Space Grotesk', sans-serif;
    letter-spacing: -0.02em;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, rgba(9, 22, 38, 0.98), rgba(5, 13, 24, 0.98));
    border-right: 1px solid rgba(148, 163, 184, 0.12);
}
[data-testid="stSidebar"] .block-container { padding-top: 1.2rem; }

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 0.45rem;
    background: rgba(15, 32, 52, 0.58);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 0.38rem;
}
.stTabs [data-baseweb="tab"] {
    height: 2.75rem;
    padding: 0 1.1rem;
    border-radius: 10px;
    color: #94a3b8;
    font-weight: 600;
}
.stTabs [aria-selected="true"] {
    color: #f8fafc !important;
    background: linear-gradient(135deg, rgba(56, 189, 248, 0.22), rgba(45, 212, 191, 0.14)) !important;
    box-shadow: inset 0 0 0 1px rgba(56, 189, 248, 0.22);
}

/* Native elements */
[data-testid="stDataFrame"] {
    border: 1px solid var(--border);
    border-radius: 14px;
    overflow: hidden;
}
[data-testid="stExpander"] {
    background: rgba(15, 32, 52, 0.55);
    border: 1px solid var(--border);
    border-radius: 14px;
}
[data-testid="stAlert"] {
    border-radius: 14px;
    border: 1px solid rgba(148, 163, 184, 0.16);
}

/* Hero */
.eco-hero {
    position: relative;
    overflow: hidden;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1.5rem;
    padding: 1.35rem 1.55rem;
    margin: 0 0 1rem 0;
    border: 1px solid rgba(56, 189, 248, 0.2);
    border-radius: 22px;
    background:
        linear-gradient(135deg, rgba(18, 42, 67, 0.96), rgba(8, 23, 40, 0.94)),
        radial-gradient(circle at 80% 20%, rgba(45, 212, 191, 0.22), transparent 35%);
    box-shadow: 0 20px 70px rgba(0, 0, 0, 0.26);
}
.eco-hero::after {
    content: '';
    position: absolute;
    width: 260px;
    height: 260px;
    right: -80px;
    top: -125px;
    background: radial-gradient(circle, rgba(56, 189, 248, 0.2), transparent 67%);
}
.eco-brand { display: flex; align-items: center; gap: 1rem; z-index: 1; }
.eco-logo {
    display: grid;
    place-items: center;
    width: 58px;
    height: 58px;
    border-radius: 17px;
    font-size: 1.7rem;
    background: linear-gradient(135deg, rgba(56, 189, 248, 0.22), rgba(45, 212, 191, 0.22));
    border: 1px solid rgba(94, 234, 212, 0.28);
    box-shadow: 0 10px 35px rgba(45, 212, 191, 0.12);
}
.eco-title {
    margin: 0;
    font-family: 'Space Grotesk', sans-serif;
    font-size: clamp(1.7rem, 3vw, 2.45rem);
    font-weight: 700;
    letter-spacing: -0.045em;
    color: #f8fafc;
}
.eco-title span {
    background: linear-gradient(90deg, #7dd3fc, #5eead4);
    -webkit-background-clip: text;
    color: transparent;
}
.eco-subtitle { margin-top: 0.35rem; color: #a5b4c7; font-size: 0.93rem; }
.eco-live-wrap { display: flex; align-items: center; gap: 0.65rem; z-index: 1; flex-wrap: wrap; justify-content: flex-end; }
.eco-pill {
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
    padding: 0.52rem 0.78rem;
    border-radius: 999px;
    border: 1px solid rgba(148, 163, 184, 0.18);
    background: rgba(5, 15, 27, 0.6);
    color: #cbd5e1;
    font-size: 0.78rem;
    font-weight: 700;
    letter-spacing: 0.02em;
}
.eco-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #4ade80;
    box-shadow: 0 0 0 5px rgba(74, 222, 128, 0.1), 0 0 18px rgba(74, 222, 128, 0.7);
    animation: pulse 1.8s infinite;
}
.eco-dot.offline { background: #fb7185; box-shadow: 0 0 0 5px rgba(251,113,133,.1); }
@keyframes pulse { 0%,100% { opacity:1; transform:scale(1);} 50% {opacity:.45; transform:scale(.86);} }

/* KPI cards */
.eco-kpi {
    position: relative;
    overflow: hidden;
    min-height: 132px;
    padding: 1rem 1.05rem;
    border: 1px solid var(--border);
    border-radius: 18px;
    background: linear-gradient(155deg, rgba(17, 38, 61, 0.88), rgba(8, 21, 37, 0.82));
    box-shadow: 0 14px 34px rgba(0, 0, 0, 0.15);
    transition: transform .2s ease, border-color .2s ease, box-shadow .2s ease;
}
.eco-kpi:hover {
    transform: translateY(-3px);
    border-color: rgba(56, 189, 248, 0.32);
    box-shadow: 0 20px 44px rgba(0, 0, 0, 0.22);
}
.eco-kpi::after {
    content: '';
    position: absolute;
    width: 88px;
    height: 88px;
    top: -42px;
    right: -32px;
    border-radius: 50%;
    background: var(--accent, rgba(56, 189, 248, 0.14));
    filter: blur(2px);
}
.eco-kpi-head { display:flex; justify-content:space-between; align-items:center; gap:.5rem; }
.eco-kpi-label { color: #94a3b8; font-size: .77rem; font-weight: 700; letter-spacing: .055em; text-transform: uppercase; }
.eco-kpi-icon { font-size: 1rem; opacity: .95; }
.eco-kpi-value { margin-top: .72rem; color: #f8fafc; font-size: 1.72rem; line-height:1; font-weight: 800; letter-spacing:-.035em; }
.eco-kpi-foot { margin-top: .6rem; color: #7f91a8; font-size: .73rem; }
.eco-kpi-foot.good { color: #86efac; }
.eco-kpi-foot.warn { color: #fde68a; }
.eco-kpi-foot.bad { color: #fda4af; }

/* Section heading */
.eco-section-head { display:flex; justify-content:space-between; align-items:flex-end; margin: 1.1rem 0 .65rem; gap:1rem; }
.eco-section-title { color:#f8fafc; font-family:'Space Grotesk', sans-serif; font-size:1.08rem; font-weight:700; }
.eco-section-subtitle { color:#7f91a8; font-size:.76rem; margin-top:.18rem; }
.eco-eyebrow { color:#67e8f9; font-size:.69rem; font-weight:800; letter-spacing:.12em; text-transform:uppercase; }

/* Glass cards */
.eco-card {
    padding: 1.05rem 1.1rem;
    border: 1px solid var(--border);
    border-radius: 18px;
    background: linear-gradient(160deg, rgba(16, 35, 56, 0.76), rgba(8, 21, 37, 0.72));
    box-shadow: 0 14px 36px rgba(0,0,0,.14);
}
.eco-card-title { font-family:'Space Grotesk',sans-serif; color:#f8fafc; font-size:.98rem; font-weight:700; }
.eco-card-subtitle { color:#7f91a8; font-size:.76rem; margin-top:.2rem; }

/* Agent action */
.eco-action {
    position: relative;
    overflow:hidden;
    min-height: 210px;
    padding: 1.25rem;
    border: 1px solid rgba(45, 212, 191, .23);
    border-radius: 20px;
    background:
        linear-gradient(145deg, rgba(10, 49, 61, .88), rgba(9, 26, 43, .92));
    box-shadow: 0 18px 46px rgba(0,0,0,.2);
}
.eco-action::after {
    content:'';
    position:absolute;
    width:190px;
    height:190px;
    border-radius:50%;
    right:-90px;
    bottom:-105px;
    background:rgba(45,212,191,.12);
}
.eco-action-top { display:flex; justify-content:space-between; align-items:center; gap:1rem; }
.eco-mode {
    display:inline-flex;
    align-items:center;
    gap:.5rem;
    padding:.42rem .68rem;
    border-radius:999px;
    background:rgba(45,212,191,.12);
    border:1px solid rgba(45,212,191,.25);
    color:#99f6e4;
    font-size:.72rem;
    font-weight:800;
    letter-spacing:.08em;
}
.eco-action-reason { margin-top:1rem; color:#e2e8f0; font-size:1.02rem; line-height:1.58; max-width:92%; }
.eco-action-grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:.65rem; margin-top:1rem; }
.eco-action-stat { padding:.7rem; border-radius:12px; background:rgba(6,16,29,.44); border:1px solid rgba(148,163,184,.1); }
.eco-action-stat span { display:block; color:#7f91a8; font-size:.68rem; text-transform:uppercase; letter-spacing:.06em; font-weight:700; }
.eco-action-stat strong { display:block; margin-top:.25rem; color:#f8fafc; font-size:.92rem; }

/* Snapshot */
.eco-snapshot-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:.7rem; margin-top:.85rem; }
.eco-snapshot-item { padding:.8rem; border-radius:13px; background:rgba(6,16,29,.42); border:1px solid rgba(148,163,184,.09); }
.eco-snapshot-label { color:#7f91a8; font-size:.68rem; text-transform:uppercase; font-weight:700; letter-spacing:.06em; }
.eco-snapshot-value { color:#f8fafc; margin-top:.28rem; font-size:1.05rem; font-weight:750; }

/* Zone cards */
.eco-zone {
    min-height: 168px;
    padding: 1rem;
    border: 1px solid var(--border);
    border-radius: 16px;
    background: linear-gradient(150deg, rgba(16, 35, 56, .72), rgba(8, 21, 37, .7));
}
.eco-zone-top { display:flex; justify-content:space-between; align-items:center; gap:.5rem; }
.eco-zone-name { color:#f1f5f9; font-size:.86rem; font-weight:750; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.eco-status { padding:.28rem .5rem; border-radius:999px; font-size:.62rem; font-weight:800; letter-spacing:.05em; }
.eco-status.good { color:#86efac; background:rgba(74,222,128,.1); border:1px solid rgba(74,222,128,.17); }
.eco-status.warn { color:#fde68a; background:rgba(251,191,36,.1); border:1px solid rgba(251,191,36,.17); }
.eco-status.bad { color:#fda4af; background:rgba(251,113,133,.1); border:1px solid rgba(251,113,133,.17); }
.eco-zone-temp { margin-top:.75rem; color:#f8fafc; font-size:1.72rem; font-weight:800; letter-spacing:-.04em; }
.eco-zone-meta { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:.38rem; margin-top:.8rem; }
.eco-zone-meta div { padding:.48rem .4rem; border-radius:9px; text-align:center; background:rgba(6,16,29,.38); }
.eco-zone-meta span { display:block; color:#71849d; font-size:.59rem; text-transform:uppercase; }
.eco-zone-meta strong { display:block; color:#dbeafe; font-size:.73rem; margin-top:.15rem; }

/* Health rows */
.eco-health-row { display:flex; justify-content:space-between; align-items:center; padding:.72rem 0; border-bottom:1px solid rgba(148,163,184,.08); }
.eco-health-row:last-child { border-bottom:0; }
.eco-health-label { color:#a5b4c7; font-size:.82rem; }
.eco-health-value { color:#f8fafc; font-size:.82rem; font-weight:700; }

/* Footer */
.eco-footer { margin-top:2rem; padding-top:1rem; border-top:1px solid rgba(148,163,184,.09); color:#64748b; font-size:.72rem; text-align:center; }

@media (max-width: 900px) {
    .eco-hero { align-items:flex-start; flex-direction:column; }
    .eco-live-wrap { justify-content:flex-start; }
    .eco-action-grid { grid-template-columns:1fr; }
}
</style>
"""


def inject_theme() -> None:
    st.markdown(APP_CSS, unsafe_allow_html=True)


def _safe(value: Any) -> str:
    return html.escape(str(value))


def render_hero(*, live: bool, progress: float, mode: str = "AUTONOMOUS") -> None:
    dot_class = "eco-dot" if live else "eco-dot offline"
    status = "LIVE SIMULATION" if live else "WAITING FOR DATA"
    st.markdown(
        f"""
        <div class="eco-hero">
            <div class="eco-brand">
                <div class="eco-logo">⌁</div>
                <div>
                    <div class="eco-title"><span>EcoPilot</span> Control Center</div>
                    <div class="eco-subtitle">Safety-constrained autonomous optimization for an EnergyPlus digital twin</div>
                </div>
            </div>
            <div class="eco-live-wrap">
                <div class="eco-pill"><span class="{dot_class}"></span>{_safe(status)}</div>
                <div class="eco-pill">◉ {_safe(mode)}</div>
                <div class="eco-pill">▰ {_safe(f'{progress:.0f}% COMPLETE')}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_kpi(
    label: str,
    value: str,
    footnote: str,
    icon: str,
    tone: str = "cyan",
    footnote_tone: str = "",
) -> None:
    accents = {
        "cyan": "rgba(56, 189, 248, 0.16)",
        "teal": "rgba(45, 212, 191, 0.16)",
        "green": "rgba(74, 222, 128, 0.15)",
        "amber": "rgba(251, 191, 36, 0.15)",
        "red": "rgba(251, 113, 133, 0.15)",
        "purple": "rgba(167, 139, 250, 0.15)",
    }
    accent = accents.get(tone, accents["cyan"])
    st.markdown(
        f"""
        <div class="eco-kpi" style="--accent:{accent}">
            <div class="eco-kpi-head">
                <div class="eco-kpi-label">{_safe(label)}</div>
                <div class="eco-kpi-icon">{_safe(icon)}</div>
            </div>
            <div class="eco-kpi-value">{_safe(value)}</div>
            <div class="eco-kpi-foot {_safe(footnote_tone)}">{_safe(footnote)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_section(title: str, subtitle: str, eyebrow: str = "LIVE INTELLIGENCE") -> None:
    st.markdown(
        f"""
        <div class="eco-section-head">
            <div>
                <div class="eco-eyebrow">{_safe(eyebrow)}</div>
                <div class="eco-section-title">{_safe(title)}</div>
                <div class="eco-section-subtitle">{_safe(subtitle)}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_action_card(action: dict[str, Any] | None) -> None:
    if not action:
        st.markdown(
            """
            <div class="eco-action">
                <div class="eco-action-top">
                    <div class="eco-mode">● SAFE IDLE</div>
                </div>
                <div class="eco-action-reason">
                    No active intervention. EcoPilot is observing the building and preserving native schedules until a validated action is needed.
                </div>
                <div class="eco-action-grid">
                    <div class="eco-action-stat"><span>Safety state</span><strong>Protected</strong></div>
                    <div class="eco-action-stat"><span>Control source</span><strong>Baseline schedule</strong></div>
                    <div class="eco-action-stat"><span>Next decision</span><strong>Awaiting trigger</strong></div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    mode = action.get("mode", "UNKNOWN")
    reason = action.get("reason", "No explanation supplied.")
    confidence = float(action.get("confidence", 0.0) or 0.0) * 100
    expected = float(action.get("expected_energy_change_pct", 0.0) or 0.0)
    hold_steps = action.get("hold_steps", "—")
    source = action.get("source", "agent")

    st.markdown(
        f"""
        <div class="eco-action">
            <div class="eco-action-top">
                <div class="eco-mode">✦ {_safe(mode)}</div>
                <div class="eco-pill">VALIDATED ACTION</div>
            </div>
            <div class="eco-action-reason">{_safe(reason)}</div>
            <div class="eco-action-grid">
                <div class="eco-action-stat"><span>Confidence</span><strong>{confidence:.0f}%</strong></div>
                <div class="eco-action-stat"><span>Expected change</span><strong>{expected:+.1f}%</strong></div>
                <div class="eco-action-stat"><span>Hold / source</span><strong>{_safe(hold_steps)} steps · {_safe(source)}</strong></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_snapshot(latest: dict[str, Any] | None) -> None:
    latest = latest or {}
    outdoor = latest.get("outdoor_temperature_c")
    humidity = latest.get("outdoor_relative_humidity_pct")
    occupants = latest.get("total_occupants", 0)
    demand = latest.get("facility_kw", 0)
    values = [
        ("Outdoor", "—" if outdoor is None else f"{outdoor:.1f} °C"),
        ("Humidity", "—" if humidity is None else f"{humidity:.0f}%"),
        ("Occupants", f"{occupants:.0f}"),
        ("Live demand", f"{demand:.1f} kW"),
    ]
    items = "".join(
        f'<div class="eco-snapshot-item"><div class="eco-snapshot-label">{_safe(label)}</div>'
        f'<div class="eco-snapshot-value">{_safe(value)}</div></div>'
        for label, value in values
    )
    st.markdown(
        f"""
        <div class="eco-card" style="min-height:210px">
            <div class="eco-card-title">Building snapshot</div>
            <div class="eco-card-subtitle">Latest controlled-twin telemetry</div>
            <div class="eco-snapshot-grid">{items}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def zone_status(zone: dict[str, Any], temp_min: float, temp_max: float, co2_max: float) -> tuple[str, str]:
    temperature = zone.get("temperature_c")
    co2 = zone.get("co2_ppm")
    pmv = zone.get("pmv")
    if temperature is not None and not (temp_min <= float(temperature) <= temp_max):
        return "COMFORT RISK", "bad"
    if co2 is not None and float(co2) > co2_max:
        return "IAQ RISK", "bad"
    if pmv is not None and abs(float(pmv)) > 0.7:
        return "WATCH", "warn"
    if not zone.get("occupied"):
        return "UNOCCUPIED", "warn"
    return "OPTIMAL", "good"


def render_zone_card(zone: dict[str, Any], temp_min: float, temp_max: float, co2_max: float) -> None:
    status, tone = zone_status(zone, temp_min, temp_max, co2_max)
    temp = zone.get("temperature_c")
    co2 = zone.get("co2_ppm")
    pmv = zone.get("pmv")
    people = zone.get("occupants", 0)
    st.markdown(
        f"""
        <div class="eco-zone">
            <div class="eco-zone-top">
                <div class="eco-zone-name" title="{_safe(zone.get('name', 'Zone'))}">{_safe(zone.get('name', 'Zone'))}</div>
                <div class="eco-status {tone}">{_safe(status)}</div>
            </div>
            <div class="eco-zone-temp">{'—' if temp is None else f'{float(temp):.1f}°C'}</div>
            <div class="eco-zone-meta">
                <div><span>CO₂</span><strong>{'N/A' if co2 is None else f'{float(co2):.0f}'}</strong></div>
                <div><span>PMV</span><strong>{'N/A' if pmv is None else f'{float(pmv):+.2f}'}</strong></div>
                <div><span>People</span><strong>{float(people):.0f}</strong></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
