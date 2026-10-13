from dataclasses import dataclass
from enum import Enum


class OppositionSourceType(str, Enum):
    PERSON = "person"
    ORGANIZATION = "organization"
    ENVIRONMENT = "environment"


@dataclass(frozen=True)
class OppositionCandidate:
    source_type: OppositionSourceType
    motivation: str
    goal: str
    resources: tuple[str, ...]
    constraints: tuple[str, ...]
    relation_to_conflict: str
    conflict_id: str = ""

    def __post_init__(self):
        if not isinstance(self.source_type, OppositionSourceType):
            object.__setattr__(self, "source_type", OppositionSourceType(self.source_type))
        for field in ("motivation", "goal", "relation_to_conflict"):
            if not isinstance(getattr(self, field), str) or not getattr(self, field).strip():
                raise ValueError(f"{field} must not be empty.")
        if not isinstance(self.conflict_id, str):
            raise TypeError("conflict_id must be a string.")
        for field in ("resources", "constraints"):
            values = tuple(getattr(self, field))
            if any(not isinstance(value, str) or not value.strip() for value in values):
                raise ValueError(f"{field} must contain non-empty strings.")
            object.__setattr__(self, field, values)
