from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CharacterAgency:
    """Persistent, explainable initiative settings and recent action time."""

    character_id: str
    initiative: float = 0.5
    motivation_strength: float = 0.5
    goal_focus: float = 0.5
    action_frequency: float = 0.0
    last_action_time: str | None = None

    def __post_init__(self):
        if not isinstance(self.character_id, str) or not self.character_id.strip():
            raise ValueError("character_id must not be empty.")
        for name in ("initiative", "motivation_strength", "goal_focus", "action_frequency"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1:
                raise ValueError(f"{name} must be between 0 and 1.")
            object.__setattr__(self, name, float(value))
        if self.last_action_time is not None and (
            not isinstance(self.last_action_time, str) or not self.last_action_time.strip()
        ):
            raise ValueError("last_action_time must be None or non-empty.")
