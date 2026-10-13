from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EntryRule:
    character_id: str
    trigger_event_types: tuple[str, ...] = ()
    required_goal_types: tuple[str, ...] = ()
    allowed_locations: tuple[str, ...] = ()
    earliest_time: str | None = None
    latest_time: str | None = None

    def __post_init__(self):
        if not isinstance(self.character_id, str) or not self.character_id.strip():
            raise ValueError("character_id must not be empty.")
        for field in ("trigger_event_types", "required_goal_types", "allowed_locations"):
            values = tuple(getattr(self, field))
            if any(not isinstance(value, str) or not value.strip() for value in values):
                raise ValueError(f"{field} must contain non-empty strings.")
            object.__setattr__(self, field, values)
        for field in ("earliest_time", "latest_time"):
            value = getattr(self, field)
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise ValueError(f"{field} must be None or non-empty.")

    def matches(self, *, event_type=None, active_goal_types=(), current_location=None, current_time=None):
        triggers = []
        if self.trigger_event_types:
            triggers.append(event_type in self.trigger_event_types)
        if self.required_goal_types:
            triggers.append(bool(set(self.required_goal_types).intersection(active_goal_types)))
        if not any(triggers):
            return False
        if self.allowed_locations and current_location not in self.allowed_locations:
            return False
        if self.earliest_time and (current_time is None or current_time < self.earliest_time):
            return False
        if self.latest_time and (current_time is None or current_time > self.latest_time):
            return False
        return True
