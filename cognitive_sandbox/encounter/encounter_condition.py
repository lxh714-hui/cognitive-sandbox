from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@runtime_checkable
class EncounterCondition(Protocol):
    """Common read-only result shape implemented by the concrete conditions."""

    passed: bool
    reason: str


@dataclass(frozen=True)
class LocationCondition:
    location_a: str
    location_b: str
    passed: bool
    reason: str = ""

    def __post_init__(self):
        _strings(self.location_a, self.location_b)
        _bool_reason(self.passed, self.reason)


@dataclass(frozen=True)
class TimeCondition:
    time_a: str
    time_b: str
    passed: bool
    reason: str = ""

    def __post_init__(self):
        _strings(self.time_a, self.time_b)
        _bool_reason(self.passed, self.reason)


@dataclass(frozen=True)
class GoalCondition:
    goal_a: str = ""
    goal_b: str = ""
    passed: bool = True
    reason: str = ""

    def __post_init__(self):
        if not isinstance(self.goal_a, str) or not isinstance(self.goal_b, str):
            raise TypeError("goal labels must be strings.")
        _bool_reason(self.passed, self.reason)


@dataclass(frozen=True)
class RelationshipCondition:
    stage_a_to_b: str = "UNKNOWN"
    stage_b_to_a: str = "UNKNOWN"
    hostility: float = 0.0
    passed: bool = True
    reason: str = ""

    def __post_init__(self):
        if not isinstance(self.stage_a_to_b, str) or not isinstance(self.stage_b_to_a, str):
            raise TypeError("relationship stages must be strings.")
        if isinstance(self.hostility, bool) or not isinstance(self.hostility, (int, float)) or self.hostility < 0:
            raise ValueError("hostility must be a non-negative number.")
        object.__setattr__(self, "hostility", float(self.hostility))
        _bool_reason(self.passed, self.reason)


@dataclass(frozen=True)
class EmotionCondition:
    willingness_a: float = 0.5
    willingness_b: float = 0.5
    passed: bool = True
    reason: str = ""

    def __post_init__(self):
        for name in ("willingness_a", "willingness_b"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1:
                raise ValueError(f"{name} must be between 0 and 1.")
            object.__setattr__(self, name, float(value))
        _bool_reason(self.passed, self.reason)


@dataclass(frozen=True)
class CognitionCondition:
    cognitive_style_a: str = ""
    cognitive_style_b: str = ""
    passed: bool = True
    reason: str = ""

    def __post_init__(self):
        if not isinstance(self.cognitive_style_a, str) or not isinstance(self.cognitive_style_b, str):
            raise TypeError("cognitive style labels must be strings.")
        _bool_reason(self.passed, self.reason)


def _strings(*values):
    if any(not isinstance(value, str) or not value.strip() for value in values):
        raise ValueError("condition fields must be non-empty strings.")


def _bool_reason(passed, reason):
    if not isinstance(passed, bool) or not isinstance(reason, str):
        raise TypeError("condition requires a bool result and string reason.")


ENCOUNTER_CONDITION_TYPES = (
    LocationCondition, TimeCondition, GoalCondition, RelationshipCondition,
    EmotionCondition, CognitionCondition,
)


__all__ = [
    "EncounterCondition", "LocationCondition", "TimeCondition", "GoalCondition", "RelationshipCondition",
    "EmotionCondition", "CognitionCondition", "ENCOUNTER_CONDITION_TYPES",
]
