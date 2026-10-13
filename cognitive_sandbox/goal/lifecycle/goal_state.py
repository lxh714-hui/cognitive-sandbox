from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class GoalLifecycleState(str, Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    PROGRESSING = "PROGRESSING"
    SATISFIED = "SATISFIED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    TRANSFORMED = "TRANSFORMED"


@dataclass(frozen=True)
class GoalState:
    goal_id: str
    owner_id: str
    state: GoalLifecycleState = GoalLifecycleState.ACTIVE
    progress: float = 0.0
    # Runtime-derived feedback snapshot. Appended defaults keep old save data
    # and positional GoalState construction compatible.
    progress_velocity: float = 0.0
    stagnation_level: float = 0.0
    frustration_level: float = 0.0
    recent_action_feedback: tuple[tuple[str, str, str, str, float, float], ...] = ()
    progress_samples: tuple[tuple[str, float], ...] = ()

    def __post_init__(self):
        for key in ("goal_id", "owner_id"):
            if not isinstance(getattr(self, key), str) or not getattr(self, key).strip():
                raise ValueError(f"{key} must not be empty.")
        if not isinstance(self.state, GoalLifecycleState):
            object.__setattr__(self, "state", GoalLifecycleState(self.state))
        if isinstance(self.progress, bool) or not isinstance(self.progress, (int, float)) or not 0 <= self.progress <= 1:
            raise ValueError("progress must be between 0 and 1.")
        object.__setattr__(self, "progress", float(self.progress))
        for key in ("progress_velocity", "stagnation_level", "frustration_level"):
            value = getattr(self, key)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1:
                raise ValueError(f"{key} must be between 0 and 1.")
            object.__setattr__(self, key, float(value))
        feedback = tuple(tuple(item) for item in self.recent_action_feedback)
        if any(len(item) != 6 or any(not isinstance(value, str) for value in item[:4])
               or isinstance(item[4], bool) or not isinstance(item[4], (int, float)) or not 0 <= item[4] <= 1
               or isinstance(item[5], bool) or not isinstance(item[5], (int, float))
               for item in feedback):
            raise ValueError("recent_action_feedback entries must contain event, action, time, result, effectiveness, and progress delta.")
        object.__setattr__(self, "recent_action_feedback", tuple(
            (*item[:4], float(item[4]), float(item[5])) for item in feedback
        ))
        samples = tuple((str(when), float(progress)) for when, progress in self.progress_samples)
        if any(not 0 <= progress <= 1 for _, progress in samples):
            raise ValueError("progress samples must be between 0 and 1.")
        object.__setattr__(self, "progress_samples", samples)
