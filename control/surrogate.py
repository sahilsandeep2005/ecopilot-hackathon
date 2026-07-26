from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor

from agent.schemas import BuildingState, ControlAction


FEATURE_NAMES = [
    "facility_kw",
    "outdoor_temperature_c",
    "mean_zone_temperature_c",
    "total_occupants",
    "cooling_setpoint_c",
    "heating_setpoint_c",
    "lighting_fraction",
    "ventilation_fraction",
]


class SurrogateModel:
    """Optional next-step power predictor with a deterministic fallback.

    The hackathon controller works before this model is trained. Once enough
    rollout data exists, train and save a model to improve candidate ranking.
    """

    def __init__(self, model_path: Path | str | None = None):
        self.model_path = Path(model_path) if model_path else None
        self.model: HistGradientBoostingRegressor | None = None
        if self.model_path and self.model_path.exists():
            self.model = joblib.load(self.model_path)

    @staticmethod
    def vectorize(state: BuildingState, action: ControlAction) -> np.ndarray:
        temperatures = [zone.temperature_c for zone in state.zones if zone.temperature_c is not None]
        mean_temperature = float(np.mean(temperatures)) if temperatures else 24.0
        return np.array(
            [[
                state.facility_kw,
                state.outdoor_temperature_c or 25.0,
                mean_temperature,
                state.total_occupants,
                action.cooling_setpoint_c or 24.0,
                action.heating_setpoint_c or 20.0,
                action.lighting_fraction if action.lighting_fraction is not None else 1.0,
                action.ventilation_fraction if action.ventilation_fraction is not None else 1.0,
            ]],
            dtype=float,
        )

    def predict_kw(self, state: BuildingState, action: ControlAction) -> float:
        if self.model is not None:
            return max(0.0, float(self.model.predict(self.vectorize(state, action))[0]))

        current = max(0.0, state.facility_kw)
        cooling = action.cooling_setpoint_c if action.cooling_setpoint_c is not None else 24.0
        lighting = action.lighting_fraction if action.lighting_fraction is not None else 1.0
        ventilation = action.ventilation_fraction if action.ventilation_fraction is not None else 1.0
        cooling_effect = 0.055 * (cooling - 24.0)
        lighting_effect = 0.16 * (1.0 - lighting)
        ventilation_effect = 0.06 * (1.0 - min(ventilation, 1.0))
        reduction = max(-0.20, min(0.35, cooling_effect + lighting_effect + ventilation_effect))
        return max(0.0, current * (1.0 - reduction))

    def fit(self, features: np.ndarray, targets_kw: np.ndarray, save_to: Path | str | None = None) -> None:
        if len(features) < 25:
            raise ValueError("At least 25 training rows are required for the surrogate model.")
        model = HistGradientBoostingRegressor(max_depth=5, learning_rate=0.06, random_state=42)
        model.fit(features, targets_kw)
        self.model = model
        destination = Path(save_to) if save_to else self.model_path
        if destination:
            destination.parent.mkdir(parents=True, exist_ok=True)
            joblib.dump(model, destination)
