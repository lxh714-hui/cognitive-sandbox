from __future__ import annotations

from dataclasses import dataclass

from cognitive_sandbox.application.npc.npc_action import NpcAction


@dataclass(frozen=True)
class RoutineBehavior:
    character_id: str
    behavior_type: str
    schedule: tuple[str, ...] = ("daily",)
    priority: float = .25

    def __post_init__(self):
        for name in ("character_id", "behavior_type"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must not be empty.")
        schedule = tuple(self.schedule)
        if any(not isinstance(value, str) or not value.strip() for value in schedule):
            raise ValueError("schedule must contain non-empty strings.")
        object.__setattr__(self, "schedule", schedule)
        if isinstance(self.priority, bool) or not isinstance(self.priority, (int, float)) or not 0 <= self.priority <= 1:
            raise ValueError("priority must be between 0 and 1.")
        object.__setattr__(self, "priority", float(self.priority))

    def is_due(self, current_time) -> bool:
        if "daily" in self.schedule or "always" in self.schedule:
            return True
        if current_time is None:
            return False
        return any(value.casefold() in {str(current_time.hour), f"hour:{current_time.hour:02d}"}
                   for value in self.schedule)

    def candidate(self):
        return NpcAction(
            self.character_id, self.behavior_type,
            parameters={"routine": True}, reason=f"日常安排：{self.behavior_type}",
        )
