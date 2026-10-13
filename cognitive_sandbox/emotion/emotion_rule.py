from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EmotionRule:
    event_types: tuple[str, ...]
    deltas: tuple[tuple[str, float], ...]
    reason: str
    relationship_trust_min: float | None = None
    unrelated_deltas: tuple[tuple[str, float], ...] = ()
    learned_tendency: str | None = None

    def __post_init__(self):
        events = tuple(self.event_types)
        if not events or any(not isinstance(item, str) or not item.strip() for item in events):
            raise ValueError("event_types must contain non-empty strings.")
        object.__setattr__(self, "event_types", events)
        for field in ("deltas", "unrelated_deltas"):
            pairs = tuple((str(key), float(value)) for key, value in getattr(self, field))
            if any(not key.strip() or not -1 <= value <= 1 for key, value in pairs):
                raise ValueError(f"{field} must contain emotion delta pairs in range.")
            object.__setattr__(self, field, pairs)
        if not isinstance(self.reason, str) or not self.reason.strip():
            raise ValueError("reason must not be empty.")
        if self.relationship_trust_min is not None and not 0 <= self.relationship_trust_min <= 1:
            raise ValueError("relationship_trust_min must be between 0 and 1.")
        if self.learned_tendency is not None and not self.learned_tendency.strip():
            raise ValueError("learned_tendency must be None or non-empty.")
