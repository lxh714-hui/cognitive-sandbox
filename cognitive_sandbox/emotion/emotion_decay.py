from __future__ import annotations

from dataclasses import replace

from .emotional_state import EmotionalState


class EmotionDecay:
    """Deterministic per-day relaxation rates; guilt and attachment persist longer."""

    DEFAULT_RATES = {
        "joy": 0.12, "sadness": 0.025, "fear": 0.05, "anger": 0.08,
        "surprise": 0.35, "disgust": 0.04, "curiosity": 0.04, "guilt": 0.01,
        "attachment": 0.003, "pride": 0.015, "shame": 0.012, "hope": 0.02,
        "despair": 0.008, "stress": 0.04, "confidence": 0.005, "calmness": 0.01,
        "fatigue": 0.08,
    }
    BASELINES = {"confidence": 0.5, "calmness": 0.5}

    def __init__(self, rates=None):
        self.rates = dict(self.DEFAULT_RATES if rates is None else rates)
        for key, value in self.rates.items():
            if key not in self.DEFAULT_RATES or not 0 <= value <= 1:
                raise ValueError("decay rates must use known emotion fields and values in 0..1.")

    def apply(self, state: EmotionalState, elapsed_days: float) -> EmotionalState:
        if not isinstance(state, EmotionalState):
            raise TypeError("state must be EmotionalState.")
        if isinstance(elapsed_days, bool) or not isinstance(elapsed_days, (int, float)) or elapsed_days < 0:
            raise ValueError("elapsed_days must be non-negative.")
        changes = {}
        for field, rate in self.rates.items():
            baseline = self.BASELINES.get(field, 0.0)
            factor = max(0.0, 1.0 - rate) ** float(elapsed_days)
            changes[field] = baseline + (getattr(state, field) - baseline) * factor
        return replace(state, **{key: min(1.0, max(0.0, value)) for key, value in changes.items()})
