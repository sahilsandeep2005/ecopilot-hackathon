# EcoPilot Architecture

## Components

1. **Baseline EnergyPlus twin** — native schedules, no external actuation.
2. **Controlled EnergyPlus twin** — identical IDF and weather, with Runtime API callbacks.
3. **SQLite communication bus** — durable state, action, and event exchange between processes.
4. **MCP server** — typed tools for state retrieval, optimization, validation, actuation, and recovery.
5. **Ollama supervisory agent** — uses the MCP tool list dynamically and performs a bounded tool loop.
6. **Deterministic optimizer** — ranks candidate control modes using predicted power and penalty terms.
7. **Safety shield** — enforces hard comfort, IAQ, setpoint, deadband, and confidence constraints.
8. **Approval tokens** — HMAC-bound to the exact action and valid only for a few simulation steps.
9. **Controlled-twin runtime recheck** — validates the action again immediately before actuation.
10. **Streamlit dashboard** — displays energy, peak demand, comfort, IAQ, actions, and runtime events.

## Closed loop

```text
EnergyPlus state
    -> SQLite state bus
    -> MCP get_live_building_state
    -> LLM supervisory reasoning
    -> MCP optimize_control_action
    -> MCP validate_control_action
    -> action-bound approval token
    -> MCP apply_control_action
    -> SQLite approved action queue
    -> controlled EnergyPlus runtime safety recheck
    -> schedule actuators
    -> next EnergyPlus state
```

## Why the LLM does not directly calculate setpoints

The LLM selects a strategy and invokes tools. Numerical candidate generation and hard safety
checks are deterministic. This prevents malformed model output or hallucinated sensor values
from directly reaching EnergyPlus actuators.

## Process isolation

The baseline twin, controlled twin, MCP server, LLM agent, and dashboard run as separate
processes. A failure or slowdown in the LLM cannot terminate the EnergyPlus process. The
controlled twin continues with the last safe action for its hold period, then returns to native
schedules.

## Data and prompt latency

The agent reads compact structured states rather than raw EnergyPlus logs. EnergyPlus warnings
and errors are accessed only through a separate runtime-message tool. The fast control callback
never waits for an LLM response; it consumes already approved actions from the queue.
