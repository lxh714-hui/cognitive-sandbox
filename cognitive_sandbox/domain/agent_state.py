from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class AgentDynamicState:
    character_id: str
    confidence: float
    stress: float
    motivation: float

    def __post_init__(self) -> None:
        if not isinstance(self.character_id, str) or not self.character_id.strip():
            raise ValueError("character_id must not be empty.")
        for name in ("confidence", "stress", "motivation"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(f"{name} must be a number between 0 and 1.")
            if not math.isfinite(value) or not 0 <= value <= 1:
                raise ValueError(f"{name} must be between 0 and 1.")
            object.__setattr__(self, name, float(value))
