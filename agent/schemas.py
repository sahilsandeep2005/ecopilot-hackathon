from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


ControlMode = Literal[
    "NORMAL",
    "ECO",
    "PRECOOL",
    "PEAK_LIMIT",
    "IAQ_RECOVERY",
    "UNOCCUPIED_SETBACK",
    "COMFORT_RECOVERY",
    "SAFE_FALLBACK",
]


class ZoneState(BaseModel):
    name: str
    temperature_c: float | None = None
    relative_humidity_pct: float | None = None
    pmv: float | None = None
    co2_ppm: float | None = None
    occupants: float = 0.0
    occupied: bool = False
    cooling_setpoint_c: float | None = None
    heating_setpoint_c: float | None = None


class BuildingState(BaseModel):
    run_id: str
    mode: Literal["baseline", "controlled"]
    sim_step: int
    sim_time_hours: float
    timestamp_utc: str
    calendar: dict[str, int | float] = Field(default_factory=dict)
    outdoor_temperature_c: float | None = None
    outdoor_relative_humidity_pct: float | None = None
    facility_kw: float = 0.0
    cumulative_kwh: float = 0.0
    peak_kw: float = 0.0
    hvac_kwh: float | None = None
    total_occupants: float = 0.0
    zones: list[ZoneState] = Field(default_factory=list)
    active_action: dict[str, Any] | None = None
    available_signals: list[str] = Field(default_factory=list)
    runtime: dict[str, Any] = Field(default_factory=dict)


class ControlAction(BaseModel):
    action_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    mode: ControlMode = "NORMAL"
    cooling_setpoint_c: float | None = None
    heating_setpoint_c: float | None = None
    lighting_fraction: float | None = None
    ventilation_fraction: float | None = None
    hold_steps: int = Field(default=2, ge=1, le=16)
    force_when_unoccupied: bool = False
    reset_to_baseline: bool = False
    reason: str = Field(min_length=3, max_length=500)
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    expected_energy_change_pct: float | None = Field(default=None, ge=-100.0, le=100.0)
    created_for_step: int = Field(default=0, ge=0)
    source: str = Field(default="llm", max_length=80)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("lighting_fraction")
    @classmethod
    def validate_lighting_fraction(cls, value: float | None) -> float | None:
        if value is not None and not 0.0 <= value <= 1.0:
            raise ValueError("lighting_fraction must be between 0 and 1")
        return value

    @field_validator("ventilation_fraction")
    @classmethod
    def validate_ventilation_fraction(cls, value: float | None) -> float | None:
        if value is not None and not 0.0 <= value <= 2.0:
            raise ValueError("ventilation_fraction must be between 0 and 2")
        return value

    def canonical_payload(self) -> bytes:
        value = self.model_dump(mode="json", exclude_none=False)
        text = json.dumps(value, sort_keys=True, separators=(",", ":"))
        return text.encode("utf-8")

    def digest(self) -> str:
        return hashlib.sha256(self.canonical_payload()).hexdigest()


class ValidationResult(BaseModel):
    approved: bool
    reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    approval_token: str | None = None
    expires_at_step: int | None = None
    action: ControlAction | None = None


class OptimizationCandidate(BaseModel):
    action: ControlAction
    predicted_kw: float
    energy_score: float
    comfort_penalty: float
    iaq_penalty: float
    switching_penalty: float
    total_score: float


class OptimizationResult(BaseModel):
    selected_action: ControlAction
    candidates: list[OptimizationCandidate]
    state_step: int
    explanation: str
