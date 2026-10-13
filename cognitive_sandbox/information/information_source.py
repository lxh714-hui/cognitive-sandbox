from dataclasses import dataclass
from enum import Enum


class InformationSourceType(str, Enum):
    DIRECT_OBSERVATION = "DIRECT_OBSERVATION"
    PERSONAL_MEMORY = "PERSONAL_MEMORY"
    RUMOR = "RUMOR"
    DOCUMENT = "DOCUMENT"
    REPORT = "REPORT"


@dataclass(frozen=True)
class InformationSource:
    source_type: InformationSourceType
    source_id: str
    description: str
    actor_id: str | None = None

    def __post_init__(self):
        if not isinstance(self.source_type, InformationSourceType):
            object.__setattr__(self, "source_type", InformationSourceType(self.source_type))
        for name in ("source_id", "description"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must not be empty")
        if self.actor_id is not None and (not isinstance(self.actor_id, str) or not self.actor_id.strip()):
            raise ValueError("actor_id must be non-empty or None")
