from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType


@dataclass(frozen=True)
class EmotionalMemory:
    event_id: str
    emotional_impact: Mapping[str, float]
    learned_tendency: str
    persistence: float

    def __post_init__(self):
        if not isinstance(self.event_id, str) or not self.event_id.strip():
            raise ValueError("event_id must not be empty.")
        if not isinstance(self.learned_tendency, str) or not self.learned_tendency.strip():
            raise ValueError("learned_tendency must not be empty.")
        if not isinstance(self.emotional_impact, Mapping):
            raise TypeError("emotional_impact must be a mapping.")
        impact = dict(self.emotional_impact)
        if any(not isinstance(key, str) or not key.strip() or isinstance(value, bool)
               or not isinstance(value, (int, float)) or not -1 <= value <= 1 for key, value in impact.items()):
            raise ValueError("emotional_impact must map names to deltas in -1..1.")
        object.__setattr__(self, "emotional_impact", MappingProxyType({key: float(value) for key, value in impact.items()}))
        if isinstance(self.persistence, bool) or not isinstance(self.persistence, (int, float)) or not 0 <= self.persistence <= 1:
            raise ValueError("persistence must be between 0 and 1.")
        object.__setattr__(self, "persistence", float(self.persistence))
