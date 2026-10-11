from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class NarrativeEvent:
    source_event_id: str
    title: str
    description: str
    participants: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in ("source_event_id", "title", "description"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must not be empty.")
        if isinstance(self.participants, (str, bytes)):
            raise TypeError("participants must be a collection of participant IDs.")
        participants = tuple(self.participants)
        if any(not isinstance(value, str) or not value.strip() for value in participants):
            raise ValueError("participants must contain non-empty strings.")
        object.__setattr__(self, "participants", participants)
