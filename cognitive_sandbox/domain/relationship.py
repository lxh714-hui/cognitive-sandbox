from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class RelationshipState:
    source_id: str
    target_id: str
    relation_type: str
    trust: float

    def __post_init__(self) -> None:
        for name in ("source_id", "target_id", "relation_type"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must not be empty.")
        if isinstance(self.trust, bool) or not isinstance(self.trust, (int, float)):
            raise TypeError("trust must be a number between 0 and 1.")
        if not math.isfinite(self.trust) or not 0 <= self.trust <= 1:
            raise ValueError("trust must be between 0 and 1.")
        object.__setattr__(self, "trust", float(self.trust))
