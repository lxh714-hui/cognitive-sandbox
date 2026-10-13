from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class RelationshipRule:
    event_types: tuple[str, ...]
    trust_delta: float = 0.0
    respect_delta: float = 0.0
    fear_delta: float = 0.0
    affinity_delta: float = 0.0
    hostility_delta: float = 0.0
    direction: str = "actor_to_target"

    def __post_init__(self):
        values = (self.event_types,) if isinstance(self.event_types, str) else tuple(self.event_types)
        if not values or any(not isinstance(item, str) or not item.strip() for item in values):
            raise ValueError("event_types must contain non-empty event type names.")
        object.__setattr__(self, "event_types", values)
        if self.direction not in {"actor_to_target", "target_to_actor", "both"}:
            raise ValueError("direction must be actor_to_target, target_to_actor, or both.")
        for name in ("trust_delta", "respect_delta", "fear_delta", "affinity_delta", "hostility_delta"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(f"{name} must be numeric.")
            if not math.isfinite(value):
                raise ValueError(f"{name} must be finite.")
