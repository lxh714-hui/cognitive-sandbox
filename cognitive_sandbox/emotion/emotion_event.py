from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EmotionEvent:
    character_id: str
    source_event_id: str
    emotion_type: str
    delta: float
    reason: str
    timestamp: str

    def __post_init__(self):
        for field in ("character_id", "source_event_id", "emotion_type", "reason", "timestamp"):
            value = getattr(self, field)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field} must not be empty.")
        if isinstance(self.delta, bool) or not isinstance(self.delta, (int, float)) or not -1 <= self.delta <= 1:
            raise ValueError("delta must be between -1 and 1.")
        object.__setattr__(self, "delta", float(self.delta))
