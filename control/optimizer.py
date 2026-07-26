from __future__ import annotations

import math
from pathlib import Path

from agent.schemas import (
    BuildingState,
    ControlAction,
    OptimizationCandidate,
    OptimizationResult,
)
from control.constraints import ConstraintChecker
from control.fallback_controller import safe_fallback_action
from control.surrogate import SurrogateModel
from core.config import settings


class ControlOptimizer:
    def __init__(self, surrogate_path: Path | str | None = None):
        self.surrogate = SurrogateModel(surrogate_path)
        self.constraints = ConstraintChecker()

    @staticmethod
    def _mean(values: list[float]) -> float | None:
        return sum(values) / len(values) if values else None

    def _candidate_actions(self, state: BuildingState) -> list[ControlAction]:
        occupied = [zone for zone in state.zones if zone.occupied]
        mean_temp = self._mean([zone.temperature_c for zone in occupied if zone.temperature_c is not None])
        mean_pmv = self._mean([zone.pmv for zone in occupied if zone.pmv is not None])
        max_co2 = max([zone.co2_ppm for zone in occupied if zone.co2_ppm is not None], default=None)
        hour = int(state.calendar.get("hour", 0))
        current_kw = state.facility_kw
        near_peak = state.peak_kw > 0 and current_kw >= 0.92 * state.peak_kw

        candidates = [
            ControlAction(
                mode="NORMAL",
                cooling_setpoint_c=24.5,
                heating_setpoint_c=20.5,
                lighting_fraction=0.95,
                ventilation_fraction=1.0,
                hold_steps=2,
                reason="Maintain conservative comfort with a small efficiency improvement.",
                confidence=0.92,
                created_for_step=state.sim_step,
                source="optimizer",
            ),
            ControlAction(
                mode="ECO",
                cooling_setpoint_c=25.5,
                heating_setpoint_c=20.0,
                lighting_fraction=0.82,
                ventilation_fraction=0.80,
                hold_steps=3,
                reason="Use a wider but safe comfort band while reducing lighting and ventilation load.",
                confidence=0.86,
                created_for_step=state.sim_step,
                source="optimizer",
            ),
            ControlAction(
                mode="PEAK_LIMIT",
                cooling_setpoint_c=26.0,
                heating_setpoint_c=19.5,
                lighting_fraction=0.70,
                ventilation_fraction=0.75,
                hold_steps=2,
                reason="Limit facility demand during a detected peak while preserving hard constraints.",
                confidence=0.84,
                created_for_step=state.sim_step,
                source="optimizer",
            ),
        ]

        if not occupied:
            candidates.append(
                ControlAction(
                    mode="UNOCCUPIED_SETBACK",
                    reset_to_baseline=True,
                    hold_steps=2,
                    reason="No occupied zones are detected; retain the model's native unoccupied schedules.",
                    confidence=0.99,
                    created_for_step=state.sim_step,
                    source="optimizer",
                )
            )

        if (
            occupied
            and 11 <= hour <= 14
            and (state.outdoor_temperature_c or 0) >= 31.0
            and (mean_temp is None or mean_temp < 24.8)
        ):
            candidates.append(
                ControlAction(
                    mode="PRECOOL",
                    cooling_setpoint_c=23.5,
                    heating_setpoint_c=20.0,
                    lighting_fraction=0.90,
                    ventilation_fraction=0.90,
                    hold_steps=2,
                    reason="Pre-cool before the expected afternoon cooling peak.",
                    confidence=0.82,
                    expected_energy_change_pct=4.0,
                    created_for_step=state.sim_step,
                    source="optimizer",
                )
            )

        if max_co2 is not None and max_co2 >= settings.max_co2_ppm - 120:
            candidates.append(
                ControlAction(
                    mode="IAQ_RECOVERY",
                    cooling_setpoint_c=24.5,
                    heating_setpoint_c=20.5,
                    lighting_fraction=0.95,
                    ventilation_fraction=1.20,
                    hold_steps=2,
                    reason="Increase outdoor air because occupied-zone CO₂ is approaching its limit.",
                    confidence=0.98,
                    created_for_step=state.sim_step,
                    source="optimizer",
                )
            )

        if (mean_temp is not None and mean_temp >= settings.occupied_temp_max_c - 0.4) or (
            mean_pmv is not None and mean_pmv >= settings.max_abs_pmv - 0.1
        ):
            candidates.append(
                ControlAction(
                    mode="COMFORT_RECOVERY",
                    cooling_setpoint_c=24.0,
                    heating_setpoint_c=20.5,
                    lighting_fraction=1.0,
                    ventilation_fraction=1.0,
                    hold_steps=2,
                    reason="Prioritize comfort because an occupied zone is approaching the warm limit.",
                    confidence=0.99,
                    created_for_step=state.sim_step,
                    source="optimizer",
                )
            )

        if near_peak:
            for candidate in candidates:
                if candidate.mode == "PEAK_LIMIT":
                    candidate.metadata["peak_event"] = True

        return candidates

    def _score(self, state: BuildingState, action: ControlAction) -> OptimizationCandidate:
        predicted_kw = self.surrogate.predict_kw(state, action)
        energy_score = predicted_kw

        occupied = [zone for zone in state.zones if zone.occupied]
        comfort_penalty = 0.0
        iaq_penalty = 0.0
        for zone in occupied:
            if zone.temperature_c is not None:
                projected = zone.temperature_c
                if action.cooling_setpoint_c is not None and zone.temperature_c > action.cooling_setpoint_c:
                    projected -= min(0.5, 0.25 * (zone.temperature_c - action.cooling_setpoint_c))
                if projected > settings.occupied_temp_max_c:
                    comfort_penalty += 1000.0 * (projected - settings.occupied_temp_max_c) ** 2
                elif projected < settings.occupied_temp_min_c:
                    comfort_penalty += 1000.0 * (settings.occupied_temp_min_c - projected) ** 2
                else:
                    comfort_penalty += 1.5 * abs(projected - 24.0)
            if zone.pmv is not None and abs(zone.pmv) > settings.max_abs_pmv:
                comfort_penalty += 1500.0 * (abs(zone.pmv) - settings.max_abs_pmv) ** 2
            if zone.co2_ppm is not None:
                ventilation = action.ventilation_fraction if action.ventilation_fraction is not None else 1.0
                projected_co2 = zone.co2_ppm * (1.0 + max(0.0, 1.0 - ventilation) * 0.08)
                if projected_co2 > settings.max_co2_ppm:
                    iaq_penalty += 3.0 * (projected_co2 - settings.max_co2_ppm)

        switching_penalty = 0.0
        active = state.active_action or {}
        if action.cooling_setpoint_c is not None and active.get("cooling_setpoint_c") is not None:
            switching_penalty += 2.0 * abs(action.cooling_setpoint_c - float(active["cooling_setpoint_c"]))
        if action.lighting_fraction is not None and active.get("lighting_fraction") is not None:
            switching_penalty += 10.0 * abs(action.lighting_fraction - float(active["lighting_fraction"]))

        if action.mode == "PRECOOL":
            energy_score += 0.08 * max(state.facility_kw, 1.0)
        if action.mode == "SAFE_FALLBACK":
            energy_score += 0.03 * max(state.facility_kw, 1.0)

        total = energy_score + comfort_penalty + iaq_penalty + switching_penalty
        return OptimizationCandidate(
            action=action,
            predicted_kw=predicted_kw,
            energy_score=energy_score,
            comfort_penalty=comfort_penalty,
            iaq_penalty=iaq_penalty,
            switching_penalty=switching_penalty,
            total_score=total,
        )

    def optimize(self, state: BuildingState) -> OptimizationResult:
        candidates: list[OptimizationCandidate] = []
        for action in self._candidate_actions(state):
            errors, _ = self.constraints.validate(action, state)
            if not errors:
                candidates.append(self._score(state, action))

        if not candidates:
            fallback = safe_fallback_action(state, "No optimizer candidate passed the safety constraints")
            candidates = [self._score(state, fallback)]

        candidates.sort(key=lambda candidate: candidate.total_score)
        selected = candidates[0].action
        if state.facility_kw > 0:
            selected.expected_energy_change_pct = (
                (state.facility_kw - candidates[0].predicted_kw) / state.facility_kw * 100.0
            )
        return OptimizationResult(
            selected_action=selected,
            candidates=candidates,
            state_step=state.sim_step,
            explanation=(
                f"Selected {selected.mode} with predicted demand "
                f"{candidates[0].predicted_kw:.2f} kW and objective {candidates[0].total_score:.2f}."
            ),
        )
