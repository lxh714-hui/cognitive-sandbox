from __future__ import annotations

from dataclasses import dataclass, fields


_FIELDS = (
    "joy", "sadness", "fear", "anger", "surprise", "disgust",
    "curiosity", "guilt", "attachment", "pride", "shame", "hope", "despair",
    "stress", "confidence", "calmness", "fatigue",
)


@dataclass(frozen=True)
class EmotionalState:
    joy: float = 0.0
    sadness: float = 0.0
    fear: float = 0.0
    anger: float = 0.0
    surprise: float = 0.0
    disgust: float = 0.0
    curiosity: float = 0.0
    guilt: float = 0.0
    attachment: float = 0.0
    pride: float = 0.0
    shame: float = 0.0
    hope: float = 0.0
    despair: float = 0.0
    stress: float = 0.0
    confidence: float = 0.5
    calmness: float = 0.5
    fatigue: float = 0.0

    def __post_init__(self):
        for field in fields(self):
            value = getattr(self, field.name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1:
                raise ValueError(f"{field.name} must be between 0 and 1.")
            object.__setattr__(self, field.name, float(value))

    def as_dict(self):
        return {name: getattr(self, name) for name in _FIELDS}


EMOTION_FIELDS = _FIELDS
