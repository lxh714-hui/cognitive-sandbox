from dataclasses import dataclass
from enum import Enum

from .conflict_type import ConflictType


class ConflictStatus(str, Enum):
    EMERGING = "emerging"
    ACTIVE = "active"
    ESCALATING = "escalating"
    STABLE = "stable"
    RESOLVED = "resolved"
    TRANSFORMED = "transformed"
    ACCEPTED = "accepted"
    # Kept for saves and callers from Phase 13.3.
    ESCALATED = "escalated"


class ConflictParticipantRole(str, Enum):
    INITIATOR = "initiator"
    OPPOSER = "opposer"
    AFFECTED = "affected"


class ConflictResponseType(str, Enum):
    AVOID = "avoid"
    NEGOTIATE = "negotiate"
    COOPERATE = "cooperate"
    COMPETE = "compete"
    ESCALATE = "escalate"
    TRANSFORM = "transform"


@dataclass(frozen=True)
class ConflictResponseCandidate:
    response_type: ConflictResponseType
    score: float

    def __post_init__(self):
        if not isinstance(self.response_type, ConflictResponseType):
            object.__setattr__(self, "response_type", ConflictResponseType(self.response_type))
        if isinstance(self.score, bool) or not isinstance(self.score, (int, float)) or not 0 <= self.score <= 1:
            raise ValueError("score must be between 0 and 1.")
        object.__setattr__(self, "score", float(self.score))


@dataclass(frozen=True)
class ConflictParticipant:
    character_id: str
    conflict_id: str
    role: ConflictParticipantRole
    motivation: str
    available_response_types: tuple[ConflictResponseType, ...] = tuple(ConflictResponseType)

    def __post_init__(self):
        for field in ("character_id", "conflict_id", "motivation"):
            if not isinstance(getattr(self, field), str) or not getattr(self, field).strip():
                raise ValueError(f"{field} must not be empty.")
        if not isinstance(self.role, ConflictParticipantRole):
            object.__setattr__(self, "role", ConflictParticipantRole(self.role))
        values = tuple(value if isinstance(value, ConflictResponseType) else ConflictResponseType(value)
                       for value in self.available_response_types)
        object.__setattr__(self, "available_response_types", values)


@dataclass(frozen=True)
class GoalPressure:
    goal_id: str
    reason: str
    severity: float

    def __post_init__(self):
        if not isinstance(self.goal_id, str) or not self.goal_id.strip():
            raise ValueError("goal_id must not be empty.")
        if not isinstance(self.reason, str) or not self.reason.strip():
            raise ValueError("reason must not be empty.")
        if isinstance(self.severity, bool) or not isinstance(self.severity, (int, float)) or not 0 <= self.severity <= 1:
            raise ValueError("severity must be between 0 and 1.")
        object.__setattr__(self, "severity", float(self.severity))


@dataclass(frozen=True, init=False)
class ConflictState:
    id: str
    conflict_type: ConflictType
    participants: tuple[str, ...]
    related_goals: tuple[str, ...] = ()
    related_resources: tuple[str, ...] = ()
    severity: float = 0.0
    status: ConflictStatus = ConflictStatus.ACTIVE
    created_time: str = ""
    description: str = ""
    response_actions: tuple[str, ...] = ()
    participant_details: tuple[ConflictParticipant, ...] = ()
    updated_time: str = ""
    evolution_count: int = 0
    baseline_severity: float | None = None
    cause: str = ""
    related_beliefs: tuple[str, ...] = ()
    created_from: str | None = None
    resolved_by: str | None = None
    intensity: float | None = None
    pressure: float | None = None

    def __init__(self, id, conflict_type=None, participants=(), related_goals=(), related_resources=(),
                 severity=0.0, status=ConflictStatus.ACTIVE, created_time="", description="",
                 response_actions=(), participant_details=(), updated_time="", evolution_count=0,
                 baseline_severity=None, cause="", related_beliefs=(), created_from=None,
                 resolved_by=None, intensity=None, pressure=None, *, type=None):
        if conflict_type is not None and type is not None and conflict_type != type:
            raise ValueError("type and conflict_type must match when both are provided.")
        conflict_type = conflict_type if conflict_type is not None else type
        if conflict_type is None:
            raise ValueError("type must not be empty.")
        values = {
            "id": id, "conflict_type": conflict_type, "participants": participants,
            "related_goals": related_goals, "related_resources": related_resources,
            "severity": severity, "status": status, "created_time": created_time,
            "description": description, "response_actions": response_actions,
            "participant_details": participant_details, "updated_time": updated_time,
            "evolution_count": evolution_count, "baseline_severity": baseline_severity,
            "cause": cause, "related_beliefs": related_beliefs, "created_from": created_from,
            "resolved_by": resolved_by, "intensity": intensity, "pressure": pressure,
        }
        for name, value in values.items():
            object.__setattr__(self, name, value)
        self.__post_init__()

    def __post_init__(self):
        if not isinstance(self.id, str) or not self.id.strip():
            raise ValueError("id must not be empty.")
        if not isinstance(self.conflict_type, ConflictType):
            object.__setattr__(self, "conflict_type", ConflictType(self.conflict_type))
        if not isinstance(self.status, ConflictStatus):
            object.__setattr__(self, "status", ConflictStatus(self.status))
        for field in ("participants", "related_goals", "related_resources", "response_actions", "related_beliefs"):
            values = tuple(getattr(self, field))
            if any(not isinstance(item, str) or not item.strip() for item in values):
                raise ValueError(f"{field} must contain non-empty strings.")
            object.__setattr__(self, field, values)
        if isinstance(self.severity, bool) or not isinstance(self.severity, (int, float)) or not 0 <= self.severity <= 1:
            raise ValueError("severity must be between 0 and 1.")
        intensity = self.severity if self.intensity is None else self.intensity
        if isinstance(intensity, bool) or not isinstance(intensity, (int, float)) or not 0 <= intensity <= 1:
            raise ValueError("intensity must be between 0 and 1.")
        pressure = intensity if self.pressure is None else self.pressure
        if isinstance(pressure, bool) or not isinstance(pressure, (int, float)) or not 0 <= pressure <= 1:
            raise ValueError("pressure must be between 0 and 1.")
        object.__setattr__(self, "severity", float(intensity))
        object.__setattr__(self, "intensity", float(intensity))
        object.__setattr__(self, "pressure", float(pressure))
        if self.baseline_severity is not None:
            if isinstance(self.baseline_severity, bool) or not isinstance(self.baseline_severity, (int, float)) or not 0 <= self.baseline_severity <= 1:
                raise ValueError("baseline_severity must be None or between 0 and 1.")
            object.__setattr__(self, "baseline_severity", float(self.baseline_severity))
        for field in ("created_time", "description", "cause"):
            if not isinstance(getattr(self, field), str):
                raise TypeError(f"{field} must be a string.")
        if not self.cause:
            object.__setattr__(self, "cause", self.description)
        elif not self.description:
            object.__setattr__(self, "description", self.cause)
        if not isinstance(self.updated_time, str):
            raise TypeError("updated_time must be a string.")
        for field in ("created_from", "resolved_by"):
            value = getattr(self, field)
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise ValueError(f"{field} must be None or a non-empty string.")
        details = tuple(self.participant_details)
        if any(not isinstance(item, ConflictParticipant) for item in details):
            raise TypeError("participant_details must contain ConflictParticipant values.")
        object.__setattr__(self, "participant_details", details)
        if isinstance(self.evolution_count, bool) or not isinstance(self.evolution_count, int) or self.evolution_count < 0:
            raise ValueError("evolution_count must be non-negative.")

    def with_response(self, action_type):
        actions = self.response_actions if action_type in self.response_actions else (*self.response_actions, action_type)
        return ConflictState(self.id, self.conflict_type, self.participants, self.related_goals,
                             self.related_resources, self.severity, self.status, self.created_time,
                             self.description, actions, self.participant_details, self.updated_time,
                             self.evolution_count, self.baseline_severity, self.cause,
                             self.related_beliefs, self.created_from, self.resolved_by,
                             self.intensity, self.pressure)

    @property
    def type(self):
        """Preferred narrative-facing name; conflict_type remains for old callers/saves."""
        return self.conflict_type

