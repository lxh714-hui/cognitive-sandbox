from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GoalTransitionRule:
    source_goal: str
    condition: str
    result: str
    result_description: str = ""
    result_priority: float = 0.7
    result_conditions: tuple[str, ...] = ()

    def __post_init__(self):
        for name in ("source_goal", "condition", "result"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name).strip():
                raise ValueError(f"{name} must not be empty.")
        if not isinstance(self.result_description, str):
            raise TypeError("result_description must be a string.")
        if isinstance(self.result_priority, bool) or not isinstance(self.result_priority, (int, float)) or not 0 <= self.result_priority <= 1:
            raise ValueError("result_priority must be between 0 and 1.")
        values = tuple(self.result_conditions)
        if any(not isinstance(value, str) or not value.strip() for value in values):
            raise ValueError("result_conditions must contain non-empty strings.")
        object.__setattr__(self, "result_conditions", values)
