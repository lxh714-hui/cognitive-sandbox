from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CharacterGoal:
    owner_id: str
    description: str
    goal_type: str
    priority: float = 0.5
    conditions: tuple[str, ...] = ()
    progress: float = 0.0
    status: str = "active"
    goal_id: str = ""
    parent_goal_id: str | None = None
    subgoals: tuple[str, ...] = ()
    completion_conditions: tuple[str, ...] = ()

    def __post_init__(self):
        for name in ("owner_id", "description", "goal_type"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must not be empty.")
        for name in ("priority", "progress"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1:
                raise ValueError(f"{name} must be between 0 and 1.")
            object.__setattr__(self, name, float(value))
        conditions = tuple(self.conditions)
        if any(not isinstance(item, str) or not item.strip() for item in conditions):
            raise ValueError("conditions must contain non-empty strings.")
        object.__setattr__(self, "conditions", conditions)
        goal_id = self.goal_id or f"{self.owner_id}:{self.goal_type}"
        if not isinstance(goal_id, str) or not goal_id.strip():
            raise ValueError("goal_id must not be empty.")
        object.__setattr__(self, "goal_id", goal_id)
        if self.parent_goal_id is not None and (not isinstance(self.parent_goal_id, str) or not self.parent_goal_id.strip()):
            raise ValueError("parent_goal_id must be None or a non-empty string.")
        for name in ("subgoals", "completion_conditions"):
            values = tuple(getattr(self, name))
            if any(not isinstance(item, str) or not item.strip() for item in values):
                raise ValueError(f"{name} must contain non-empty strings.")
            object.__setattr__(self, name, values)
        if self.status not in {"active", "completed", "paused"}:
            raise ValueError("status must be active, paused, or completed.")
