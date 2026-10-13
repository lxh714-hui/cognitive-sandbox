from __future__ import annotations

from dataclasses import dataclass
from .goal_state import GoalLifecycleState


@dataclass(frozen=True)
class GoalHistoryEntry:
    owner_id: str
    goal_id: str
    previous_state: GoalLifecycleState
    new_state: GoalLifecycleState
    reason: str
    source_event_id: str = ""
    timestamp: str = ""

    def __post_init__(self):
        for name in ("owner_id", "goal_id", "reason"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name).strip():
                raise ValueError(f"{name} must not be empty.")
        for name in ("previous_state", "new_state"):
            value = getattr(self, name)
            if not isinstance(value, GoalLifecycleState):
                object.__setattr__(self, name, GoalLifecycleState(value))
        if not isinstance(self.source_event_id, str) or not isinstance(self.timestamp, str):
            raise TypeError("event ID and timestamp must be strings.")
