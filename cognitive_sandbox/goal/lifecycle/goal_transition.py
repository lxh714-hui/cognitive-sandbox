from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GoalTransition:
    owner_id: str
    source_goal_id: str
    target_goal_id: str
    source_event_id: str
    reason: str
    timestamp: str = ""

    def __post_init__(self):
        for name in ("owner_id", "source_goal_id", "target_goal_id", "source_event_id", "reason"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name).strip():
                raise ValueError(f"{name} must not be empty.")
        if not isinstance(self.timestamp, str):
            raise TypeError("timestamp must be a string.")
