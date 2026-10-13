from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EventQuery:
    start_time: str | None = None
    end_time: str | None = None
    event_types: tuple[str, ...] = ()
    character_ids: tuple[str, ...] = ()
    location: str | None = None
    minimum_importance: float | None = None
    maximum_importance: float | None = None

    def __post_init__(self):
        for name in ("start_time", "end_time", "location"):
            value = getattr(self, name)
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise ValueError(f"{name} must be None or a non-empty string.")
        for name in ("event_types", "character_ids"):
            values = getattr(self, name)
            if isinstance(values, (str, bytes)):
                raise TypeError(f"{name} must be a collection of strings.")
            values = tuple(values)
            if any(not isinstance(item, str) or not item.strip() for item in values):
                raise ValueError(f"{name} must contain non-empty strings.")
            object.__setattr__(self, name, values)
        for name in ("minimum_importance", "maximum_importance"):
            value = getattr(self, name)
            if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1):
                raise ValueError(f"{name} must be between 0 and 1.")
        if self.minimum_importance is not None and self.maximum_importance is not None:
            if self.minimum_importance > self.maximum_importance:
                raise ValueError("minimum_importance must not exceed maximum_importance.")

    def matches(self, record) -> bool:
        if self.start_time is not None and record.timestamp < self.start_time:
            return False
        if self.end_time is not None and record.timestamp > self.end_time:
            return False
        if self.event_types and record.event_type not in self.event_types:
            return False
        if self.character_ids and not set(self.character_ids).intersection((*record.actor_ids, *record.target_ids)):
            return False
        if self.location is not None and record.location != self.location:
            return False
        if self.minimum_importance is not None and record.importance < self.minimum_importance:
            return False
        if self.maximum_importance is not None and record.importance > self.maximum_importance:
            return False
        return True
