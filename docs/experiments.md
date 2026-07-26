# Experiment Plan

Run baseline and controlled twins with the same IDF, EPW weather, RunPeriod, timestep, and
occupancy schedules. Change only runtime actuator overrides in the controlled twin.

## Required scenarios

### 1. Normal occupied weekday
Demonstrates ordinary energy optimization and stable comfort.

### 2. Hot-weather day
Use a hot EPW period or a Delhi/Chennai weather file. Demonstrates high cooling-load behavior.

### 3. Peak-demand event
Configure a peak threshold or inject a demand event into optimizer metadata. Demonstrates
`PEAK_LIMIT` and pre-cooling.

### 4. Occupancy change
Use an IDF with meaningful occupancy schedules or create an alternate schedule. Demonstrates
that unoccupied periods return to native setback schedules.

### 5. IAQ stress
Use a model with `ZoneAirContaminantBalance` and CO₂ generation. Demonstrates that ventilation
cannot be reduced near the CO₂ limit and that `IAQ_RECOVERY` is selected.

### 6. Fault injection
Try one of these during the demo:

- Change the action after validation and reuse the token.
- Wait until the approval token expires.
- Propose a 29 °C cooling setpoint.
- Stop Ollama while the EnergyPlus process continues.
- Temporarily provide a malformed action dictionary.

The system should reject the action, log the reason, and continue or restore native schedules.

## Reported metrics

- Total baseline and controlled electricity, kWh
- Percentage energy saving
- Baseline and controlled peak demand, kW
- Percentage peak reduction
- Occupied comfort compliance
- Occupied CO₂ compliance
- Applied actions
- Rejected unsafe actions
- EnergyPlus warning and error count
- Agent/MCP latency from audit logs

## Fair-comparison warning

The current dashboard compares the latest cumulative values from each twin. For a final paper or
submission, align states by `sim_time_hours` before calculating each time-series difference,
especially when one process runs faster than the other.
