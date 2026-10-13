from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .director_intent import DirectorIntent
from .constraint_type import ConstraintType
from .constraint_target import ConstraintTarget
from .constraint_strength import ConstraintStrength


class DirectorConstraintStatus(str, Enum):
    PENDING = "PENDING"
    SEARCHING = "SEARCHING"
    ACTIVE = "ACTIVE"
    SATISFIED = "SATISFIED"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class DirectorConstraint:
    id: str
    intent: DirectorIntent
    target: str | None
    priority: float
    conditions: tuple[str, ...] = ()
    status: DirectorConstraintStatus = DirectorConstraintStatus.PENDING
    constraint_type: ConstraintType | None = None
    target_kind: ConstraintTarget | None = None
    category: str | None = None
    source: str = "player"
    strength: ConstraintStrength | None = None

    def __post_init__(self):
        if not isinstance(self.id, str) or not self.id.strip():
            raise ValueError("id must not be empty.")
        if not isinstance(self.intent, DirectorIntent):
            raise TypeError("intent must be a DirectorIntent.")
        if self.target is not None and (not isinstance(self.target, str) or not self.target.strip()):
            raise ValueError("target must be None or non-empty.")
        if isinstance(self.priority, bool) or not isinstance(self.priority, (int, float)) or not 0 <= self.priority <= 1:
            raise ValueError("priority must be between 0 and 1.")
        conditions = tuple(self.conditions)
        if any(not isinstance(item, str) or not item.strip() for item in conditions):
            raise ValueError("conditions must contain non-empty strings.")
        object.__setattr__(self, "conditions", conditions)
        if not isinstance(self.status, DirectorConstraintStatus):
            object.__setattr__(self, "status", DirectorConstraintStatus(self.status))
        object.__setattr__(self, "priority", float(self.priority))
        if self.constraint_type is None:
            object.__setattr__(self, "constraint_type", self.intent.constraint_type)
        elif not isinstance(self.constraint_type, ConstraintType):
            object.__setattr__(self, "constraint_type", ConstraintType(self.constraint_type))
        if self.target_kind is None:
            object.__setattr__(self, "target_kind", self.intent.constraint_target)
        elif not isinstance(self.target_kind, ConstraintTarget):
            object.__setattr__(self, "target_kind", ConstraintTarget(self.target_kind))
        if self.strength is None:
            object.__setattr__(self, "strength", self.intent.strength)
        elif not isinstance(self.strength, ConstraintStrength):
            object.__setattr__(self, "strength", ConstraintStrength(self.strength))
        if self.category is None:
            object.__setattr__(self, "category", self.intent.category)
        for name in ("category", "source"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name).strip():
                raise ValueError(f"{name} must not be empty.")
