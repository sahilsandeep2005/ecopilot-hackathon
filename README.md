# EcoPilot

**A safety-constrained agentic digital twin for autonomous building energy optimization**

EcoPilot is a complete hackathon starter repository for the Honeywell “Eco-Loop Building Agents”
problem. It runs two identical EnergyPlus simulations: a native-schedule baseline and an
AI-controlled twin. A local open-source LLM uses MCP tools to read the building state, request
candidate actions, validate them, queue approved controls, and recover to baseline when needed.

> This is a strong, runnable engineering scaffold—not a universal plug-and-play controller for
> every IDF. EnergyPlus actuator names and available output variables depend on the selected
> building model. The repository automatically parses thermostat and lighting schedules and
> exports all live exchange points, but you must verify the selected actuators for your final IDF.

## Main differentiators

- Live baseline-versus-controlled EnergyPlus twins
- Runtime API feedback and forward injection
- Official MCP Python SDK server
- Local Ollama model with dynamic MCP tool discovery
- Deterministic candidate optimizer
- Hard comfort, IAQ, setpoint, and deadband constraints
- HMAC approval tokens bound to the exact action
- Second safety validation inside the EnergyPlus control process
- Automatic return to native schedules
- Quantitative Streamlit dashboard and Markdown report
- Deterministic fallback when the LLM is unavailable or fails to apply an action

## Repository map

```text
ecopilot-hackathon/
├── core/                 # configuration, SQLite state/action/event bus
├── models/               # generated baseline.idf, controlled.idf, weather.epw
├── energyplus/           # Runtime API callbacks, sensors, handles, actuators
├── mcp_server/           # MCP server and tool implementations
├── agent/                # Ollama/MCP supervisory loop and Pydantic schemas
├── control/              # optimizer, surrogate, constraints, tokens, fallback
├── dashboard/            # Streamlit dashboard
├── experiments/          # dual-twin launcher, comparison, report generation
├── scripts/              # database and model preparation
├── tests/                # unit tests and optional EnergyPlus integration test
└── docs/                 # architecture, experiment plan, three-minute script
```

## 1. Install prerequisites

Use Python 3.11 or 3.12.

Install EnergyPlus and note its installation directory. The Python package `pyenergyplus` is
shipped inside the EnergyPlus installation; it is not installed from `pip`.

Install Ollama and pull a tool-capable open-source model:

```bash
ollama pull qwen3:8b
```

A larger model may improve tool selection, but a reliable 8B model is usually better than a model
that exhausts the available GPU memory.

## 2. Create the environment

### Windows PowerShell

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

### Linux or macOS

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` and set `ENERGYPLUS_HOME`.

Example Windows value:

```text
ENERGYPLUS_HOME=C:\EnergyPlusV26-2-0
```

Use the exact folder installed on your machine. The model IDF must come from the same EnergyPlus
version to avoid version-schema errors.

## 3. Prepare the model twins

```bash
python -m scripts.setup_models --days 3
```

The script searches the installed `ExampleFiles` and `WeatherData` directories, chooses a suitable
five-zone or small-office model, shortens the weather RunPeriod, and creates:

```text
models/baseline.idf
models/controlled.idf
models/weather.epw
```

The IDFs are intentionally identical. Runtime actuator overrides create the controlled case.

To use a specific model and EPW:

```bash
python scripts/setup_models.py --idf "C:\path\building.idf" --weather "C:\path\weather.epw" --days 3
```

## 4. Test the non-EnergyPlus logic

```bash
pytest
```

These tests cover the optimizer, constraints, approval tokens, IDF parsing, and SQLite bus. The
EnergyPlus integration test is skipped unless `ENERGYPLUS_HOME` is configured.

## 5. Run the complete demonstration

Ensure Ollama is running, then execute:

```bash
python -m experiments.run_scenarios
```

For an integration test without an LLM:

```bash
python -m experiments.run_scenarios --deterministic-agent
```

The launcher starts:

1. MCP server
2. Supervisory agent
3. Baseline EnergyPlus twin
4. Controlled EnergyPlus twin
5. Final report generation

Logs are written to `data/live/`. The final report is written to:

```text
data/ecopilot-report.md
```

## 6. Open the live dashboard

Run this in another terminal before or during the dual-twin experiment:

```bash
python -m streamlit run dashboard/app.py
```

The dashboard reads SQLite every two seconds and displays:

- cumulative energy comparison;
- demand comparison;
- zone temperatures and comfort boundaries;
- CO₂ when available;
- active action and explanation;
- action audit trail;
- runtime warnings and failures.

## 7. Run components manually

Manual terminals are better while debugging.

### Terminal 1 — MCP server

```bash
python -m mcp_server.server
```

Test it with MCP Inspector and connect to `http://127.0.0.1:8000/mcp`.

### Terminal 2 — agent

```bash
python -m agent.orchestrator
```

### Terminal 3 — baseline

```bash
python -m energyplus.runner --mode baseline --realtime-delay 0.05
```

### Terminal 4 — controlled twin

```bash
python -m energyplus.runner --mode controlled --realtime-delay 0.05
```

### Terminal 5 — dashboard

```bash
python -m streamlit run dashboard/app.py
```

## 8. Verify actuator discovery

After the controlled simulation initializes, inspect:

```text
data/live/exchange_points.json
```

It contains all EnergyPlus exchange points and the schedules selected for:

- cooling setpoints;
- heating setpoints;
- lighting;
- ventilation.

When automatic discovery misses a schedule, add its exact name to `.env`:

```text
CONTROLLED_COOLING_SCHEDULES=CLGSETP_SCH
CONTROLLED_HEATING_SCHEDULES=HTGSETP_SCH
CONTROLLED_LIGHTING_SCHEDULES=LIGHTS_SCH
CONTROLLED_VENTILATION_SCHEDULES=MINOA_SCH
```

Restart both simulations after changing variable or actuator requests.

## 9. PMV and CO₂ availability

PMV appears only when the IDF contains suitable `People` and thermal-comfort inputs. CO₂ appears
only when contaminant balance and CO₂ generation are configured. The code treats absent PMV/CO₂
as unavailable rather than inventing values.

For the final submission, explicitly add and validate:

- `ZoneAirContaminantBalance`;
- outdoor CO₂ schedule;
- occupant CO₂ generation;
- thermal-comfort fields in `People` objects.

Then confirm the corresponding handles in `exchange_points.json`.

## 10. Safety-token fault demonstration

Every approved action receives a token containing:

- SHA-256 digest of the exact action;
- issue simulation step;
- expiry simulation step;
- HMAC signature.

Changing any field after validation, reusing an expired token, or applying the token to another
action is rejected. This is a clear three-minute-demo example of safe agentic tool design.

## 11. Improve this starter before submission

The repository deliberately uses a conservative heuristic surrogate before training data exists.
For a winning final submission:

1. Generate rollout data over several weather and occupancy scenarios.
2. Train `control/surrogate.py` to predict next-step power and temperature.
3. Add weather and occupancy forecasts to the optimizer state.
4. Align baseline and controlled results by simulation time.
5. Add a formal peak-demand threshold or time-of-use tariff signal.
6. Run hot-day, occupancy-spike, IAQ, and LLM-failure stress tests.
7. Record action latency and predicted-versus-observed error.
8. Replace the generic building with a well-documented reference model relevant to the judges.
9. Freeze EnergyPlus, Python, model, and dependency versions in the final repository.
10. Present real measured numbers only—never placeholder savings.

## Official references

- EnergyPlus Python API: https://energyplus.readthedocs.io/en/latest/api.html
- EnergyPlus Runtime API: https://energyplus.readthedocs.io/en/latest/runtime.html
- EnergyPlus Data Transfer API: https://energyplus.readthedocs.io/en/latest/datatransfer.html
- Official MCP Python SDK: https://github.com/modelcontextprotocol/python-sdk
- Ollama tool calling: https://docs.ollama.com/capabilities/tool-calling

