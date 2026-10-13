from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class NarrativeThreadStatus(str, Enum):
    DORMANT = "DORMANT"
    POSSIBLE = "POSSIBLE"
    ACTIVE = "ACTIVE"
    ESCALATING = "ESCALATING"
    RESOLVED = "RESOLVED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class NarrativeThread:
    id: str
    title: str
    participants: tuple[str, ...]
    conflict: str
    pressure: float = 0.0
    progress: float = 0.0
    status: NarrativeThreadStatus = NarrativeThreadStatus.DORMANT
    conflict_sources: tuple[str, ...] = ()

    def __post_init__(self):
        for field in ("id", "title", "conflict"):
            value = getattr(self, field)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field} must not be empty.")
        for field in ("participants", "conflict_sources"):
            values = tuple(getattr(self, field))
            if any(not isinstance(value, str) or not value.strip() for value in values):
                raise ValueError(f"{field} must contain non-empty strings.")
            object.__setattr__(self, field, values)
        for field in ("pressure", "progress"):
            value = getattr(self, field)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1:
                raise ValueError(f"{field} must be between 0 and 1.")
            object.__setattr__(self, field, float(value))
        if not isinstance(self.status, NarrativeThreadStatus):
            object.__setattr__(self, "status", NarrativeThreadStatus(self.status))
