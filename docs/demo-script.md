# Three-Minute Demo Script

## 0:00–0:20 — Problem

“Conventional building schedules cannot continuously adapt to weather, occupancy, comfort, IAQ,
and demand. EcoPilot turns an EnergyPlus digital twin into a safety-constrained autonomous
controller.”

## 0:20–0:45 — Architecture

Show the architecture diagram and emphasize:

- identical baseline and controlled twins;
- MCP tool server;
- local open-source LLM;
- deterministic optimizer;
- safety shield and action-bound approval token;
- runtime rollback.

## 0:45–1:20 — Live state

Open the dashboard. Point to:

- live baseline and EcoPilot demand;
- cumulative energy;
- zone temperatures;
- PMV and CO₂ when the model exposes them;
- current action and reason.

## 1:20–1:55 — Tool-calling action

Show the agent log or MCP Inspector. Highlight calls to:

1. `get_live_building_state_tool`
2. `get_recent_history_tool`
3. `optimize_control_action_tool`
4. `validate_control_action_tool`
5. `apply_control_action_tool`

Show the action appear in the audit trail and the controlled setpoint change in EnergyPlus.

## 1:55–2:25 — Quantitative outcome

Show energy saving, peak reduction, comfort compliance, and IAQ compliance. Explain that both
twins use identical weather and occupancy.

## 2:25–2:45 — Fault injection

Validate one action, edit its cooling setpoint, and try to apply it with the original token. The
server should report: “The action was modified after validation.” Then queue a rollback.

## 2:45–3:00 — Close

“EcoPilot saves energy without giving an LLM unrestricted control. It is measurable, explainable,
self-correcting, and designed to fail safely.”
