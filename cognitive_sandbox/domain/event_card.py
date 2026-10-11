from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass


def _string_tuple(values: Iterable[str], field_name: str) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        raise TypeError(f"{field_name} must be a collection of strings.")
    try:
        items = tuple(values)
    except TypeError as error:
        raise TypeError(f"{field_name} must be a collection of strings.") from error
    if any(not isinstance(item, str) or not item.strip() for item in items):
        raise ValueError(f"{field_name} must contain non-empty strings.")
    return items


@dataclass(frozen=True)
class EventCard:
    event_id: str
    name: str
    description: str
    event_type: str
    participants: tuple[str, ...] = ()
    conditions: tuple[str, ...] = ()
    effects: tuple[str, ...] = ()
    priority: int = 0

    def __post_init__(self) -> None:
        for field_name in ("event_id", "name", "description", "event_type"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must not be empty.")
        for field_name in ("participants", "conditions", "effects"):
            object.__setattr__(self, field_name, _string_tuple(getattr(self, field_name), field_name))
        if isinstance(self.priority, bool) or not isinstance(self.priority, int) or self.priority < 0:
            raise ValueError("priority must be a non-negative integer.")
