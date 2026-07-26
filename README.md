# EcoPilot

> **A safety-constrained agentic digital twin for autonomous building energy optimization**

EcoPilot is an operational Physical-AI proof of concept developed for the Honeywell **Eco-Loop Building Agents** challenge.

It runs two synchronized EnergyPlus simulations:

- **Baseline Twin:** operates using native, fixed building schedules.
- **EcoPilot Twin:** receives autonomous, safety-validated runtime control actions.

A locally hosted open-source LLM uses Model Context Protocol tools to inspect live building conditions, select an operating strategy, generate candidate actions, validate safety constraints, inject approved controls into EnergyPlus, and recover to native schedules when required.

---

## Demonstrated Results

Results from the final synchronized short-run EnergyPlus experiment:

| Metric | Result |
|---|---:|
| Measured whole-building energy saving | **0.3%** |
| Occupied-zone comfort compliance | **98.0%** |
| Safety-validated actions | **27** |
| Unsafe actions applied | **0** |
| Baseline and controlled twins | **Synchronized** |
| Autonomous fallback | **Enabled** |

The measured saving is intentionally conservative because EcoPilot prioritizes thermal comfort, indoor air quality, actuator limits, thermostat deadband, and safe fallback over aggressive energy reduction.

> All values shown in this repository are generated from the EnergyPlus simulation. No savings values are manually inserted or hard-coded.

---

## Key Capabilities

- Live baseline-versus-controlled EnergyPlus digital twins
- Continuous EnergyPlus Runtime API telemetry
- Runtime actuator forward injection
- Locally hosted Qwen3 model through Ollama
- Model Context Protocol tool server
- Structured and validated LLM decisions
- Deterministic optimizer and fallback controller
- Temperature, PMV, CO₂, actuator, and deadband constraints
- HMAC-signed approval tokens tied to exact actions
- Runtime revalidation before control application
- Automatic rollback to native EnergyPlus schedules
- SQLite telemetry and action-audit store
- Premium Streamlit control-center dashboard
- Fault detection and safe-idle operation
- Baseline-versus-EcoPilot quantitative reporting

---

## System Architecture

```text
Weather, occupancy and building schedules
                    │
        ┌───────────┴───────────┐
        │                       │
┌───────▼────────┐      ┌───────▼────────┐
│ Baseline Twin  │      │ EcoPilot Twin  │
│  EnergyPlus    │      │  EnergyPlus    │
└───────┬────────┘      └───────┬────────┘
        │                       │
        │                Live telemetry
        │                       │
        │              ┌────────▼─────────┐
        │              │ State Aggregator │
        │              └────────┬─────────┘
        │                       │
        │              ┌────────▼─────────┐
        │              │ LLM Supervisor   │
        │              │ Qwen3 + Ollama   │
        │              └────────┬─────────┘
        │                       │ MCP tools
        │              ┌────────▼─────────┐
        │              │ Optimizer and    │
        │              │ Safety Shield    │
        │              └────────┬─────────┘
        │                       │
        │                Approved action
        │                       │
        │              ┌────────▼─────────┐
        │              │ Runtime Actuator │
        │              │ Forward Injection│
        │              └────────┬─────────┘
        │                       │
        └───────────┬───────────┘
                    │
             ┌──────▼──────┐
             │ Dashboard & │
             │ Audit Store │
             └─────────────┘
