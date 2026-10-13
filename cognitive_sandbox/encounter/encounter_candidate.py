from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from uuid import uuid4

from .encounter_condition import ENCOUNTER_CONDITION_TYPES


class EncounterStatus(str, Enum):
    POSSIBLE = "POSSIBLE"
    AVAILABLE = "AVAILABLE"
    REJECTED = "REJECTED"
    TRIGGERED = "TRIGGERED"
    EXPIRED = "EXPIRED"


@dataclass(frozen=True)
class EncounterTrajectory:
    character_id: str
    action_type: str
    location: str
    timestamp: str
    source_event_id: str
    public_activity: str = ""

    def __post_init__(self):
        for name in ("character_id", "action_type", "location", "timestamp", "source_event_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must not be empty.")
        if not isinstance(self.public_activity, str):
            raise TypeError("public_activity must be a string.")


@dataclass(frozen=True)
class EncounterCandidate:
    character_a: str
    character_b: str
    location: str
    time_window: str
    reason: str
    score: float
    conditions: tuple = ()
    status: EncounterStatus = EncounterStatus.POSSIBLE
    candidate_id: str = ""
    willingness_a: float = 0.5
    willingness_b: float = 0.5
    source_event_ids: tuple[str, ...] = ()
    activity_a: str = ""
    activity_b: str = ""

    def __post_init__(self):
        for name in ("character_a", "character_b", "location", "time_window", "reason"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must not be empty.")
        if self.character_a == self.character_b:
            raise ValueError("an encounter requires two distinct characters.")
        for name in ("score", "willingness_a", "willingness_b"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1:
                raise ValueError(f"{name} must be between 0 and 1.")
        object.__setattr__(self, "score", float(self.score))
        object.__setattr__(self, "willingness_a", float(self.willingness_a))
        object.__setattr__(self, "willingness_b", float(self.willingness_b))
        conditions = tuple(self.conditions)
        if any(not isinstance(item, ENCOUNTER_CONDITION_TYPES) for item in conditions):
            raise TypeError("conditions must contain encounter condition values.")
        object.__setattr__(self, "conditions", conditions)
        if not isinstance(self.status, EncounterStatus):
            object.__setattr__(self, "status", EncounterStatus(self.status))
        candidate_id = self.candidate_id or f"enc_{uuid4().hex}"
        if not isinstance(candidate_id, str) or not candidate_id.strip():
            raise ValueError("candidate_id must not be empty.")
        object.__setattr__(self, "candidate_id", candidate_id)
        refs = tuple(self.source_event_ids)
        if any(not isinstance(item, str) or not item.strip() for item in refs):
            raise ValueError("source_event_ids must contain non-empty strings.")
        object.__setattr__(self, "source_event_ids", refs)
        if not isinstance(self.activity_a, str) or not isinstance(self.activity_b, str):
            raise TypeError("activities must be strings.")


__all__ = ["EncounterCandidate", "EncounterStatus", "EncounterTrajectory"]
