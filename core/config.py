from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")


def _path_from_env(name: str, default: str) -> Path:
    raw = os.getenv(name, default)
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path.resolve()


def _csv_env(name: str) -> tuple[str, ...]:
    raw = os.getenv(name, "")
    return tuple(item.strip() for item in raw.split(",") if item.strip())


def _bool_env(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    project_root: Path = PROJECT_ROOT
    db_path: Path = _path_from_env("ECOPILOT_DB", "data/ecopilot.db")
    energyplus_home: Path | None = (
        Path(os.environ["ENERGYPLUS_HOME"]).expanduser().resolve()
        if os.getenv("ENERGYPLUS_HOME")
        else None
    )

    baseline_idf: Path = PROJECT_ROOT / "models" / "baseline.idf"
    controlled_idf: Path = PROJECT_ROOT / "models" / "controlled.idf"
    weather_file: Path = PROJECT_ROOT / "models" / "weather.epw"

    ollama_host: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "qwen3:8b")
    ollama_think: bool = _bool_env("OLLAMA_THINK", False)

    mcp_host: str = os.getenv("MCP_HOST", "127.0.0.1")
    mcp_port: int = int(os.getenv("MCP_PORT", "8000"))
    mcp_url: str = os.getenv("MCP_URL", "http://127.0.0.1:8000/mcp")

    agent_interval_seconds: float = float(os.getenv("AGENT_INTERVAL_SECONDS", "2.0"))
    agent_max_tool_rounds: int = int(os.getenv("AGENT_MAX_TOOL_ROUNDS", "8"))

    approval_secret: str = os.getenv("APPROVAL_SECRET", "change-this-before-demo")
    approval_token_valid_steps: int = int(os.getenv("APPROVAL_TOKEN_VALID_STEPS", "4"))

    occupied_temp_min_c: float = float(os.getenv("OCCUPIED_TEMP_MIN_C", "21.0"))
    occupied_temp_max_c: float = float(os.getenv("OCCUPIED_TEMP_MAX_C", "26.0"))
    max_abs_pmv: float = float(os.getenv("MAX_ABS_PMV", "0.7"))
    max_co2_ppm: float = float(os.getenv("MAX_CO2_PPM", "1000"))
    min_heating_setpoint_c: float = float(os.getenv("MIN_HEATING_SETPOINT_C", "18.0"))
    max_heating_setpoint_c: float = float(os.getenv("MAX_HEATING_SETPOINT_C", "22.0"))
    min_cooling_setpoint_c: float = float(os.getenv("MIN_COOLING_SETPOINT_C", "22.0"))
    max_cooling_setpoint_c: float = float(os.getenv("MAX_COOLING_SETPOINT_C", "27.0"))
    min_deadband_c: float = float(os.getenv("MIN_DEADBAND_C", "2.0"))
    max_setpoint_change_c: float = float(os.getenv("MAX_SETPOINT_CHANGE_C", "2.0"))

    controlled_cooling_schedules: tuple[str, ...] = _csv_env("CONTROLLED_COOLING_SCHEDULES")
    controlled_heating_schedules: tuple[str, ...] = _csv_env("CONTROLLED_HEATING_SCHEDULES")
    controlled_lighting_schedules: tuple[str, ...] = _csv_env("CONTROLLED_LIGHTING_SCHEDULES")
    controlled_ventilation_schedules: tuple[str, ...] = _csv_env("CONTROLLED_VENTILATION_SCHEDULES")

    @property
    def live_dir(self) -> Path:
        return self.project_root / "data" / "live"

    @property
    def exchange_points_path(self) -> Path:
        return self.live_dir / "exchange_points.json"


settings = Settings()
settings.db_path.parent.mkdir(parents=True, exist_ok=True)
settings.live_dir.mkdir(parents=True, exist_ok=True)
