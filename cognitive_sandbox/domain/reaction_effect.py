from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class ReactionEffect:
    reaction_id: str
    target_agent_id: str
    memory_content: str
    relationship_delta: float
    confidence_delta: float
    stress_delta: float

    def __post_init__(self) -> None:
        for name in ("reaction_id", "target_agent_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must not be empty.")
        if not isinstance(self.memory_content, str):
            raise TypeError("memory_content must be a string.")
        for name in ("relationship_delta", "confidence_delta", "stress_delta"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(f"{name} must be a number between -1 and 1.")
            if not math.isfinite(value) or not -1.0 <= value <= 1.0:
                raise ValueError(f"{name} must be between -1 and 1.")
            object.__setattr__(self, name, float(value))
