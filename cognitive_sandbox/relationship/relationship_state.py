from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class RelationshipState:
    source_id: str
    target_id: str
    trust: float = 0.0
    respect: float = 0.0
    fear: float = 0.0
    affinity: float = 0.0
    hostility: float = 0.0

    def __post_init__(self):
        for name in ("source_id", "target_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must not be empty.")
        for name in ("trust", "respect", "fear", "affinity", "hostility"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(f"{name} must be between -100 and 100.")
            if not math.isfinite(value) or not -100 <= value <= 100:
                raise ValueError(f"{name} must be between -100 and 100.")
            object.__setattr__(self, name, float(value))
