from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class InitialMemory:
    memory_id: str
    content: str
    importance: float

    def __post_init__(self) -> None:
        for name in ("memory_id", "content"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must not be empty.")
        if isinstance(self.importance, bool) or not isinstance(self.importance, (int, float)):
            raise TypeError("importance must be a number between 0 and 1.")
        if not math.isfinite(self.importance) or not 0 <= self.importance <= 1:
            raise ValueError("importance must be between 0 and 1.")
        object.__setattr__(self, "importance", float(self.importance))
