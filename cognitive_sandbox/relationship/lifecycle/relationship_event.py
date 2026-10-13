from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from collections.abc import Mapping


class RelationshipEventType(str, Enum):
    HELP = "HELP"
    BETRAY = "BETRAY"
    SHARE_INFORMATION = "SHARE_INFORMATION"
    PROTECT = "PROTECT"
    ARGUE = "ARGUE"
    COOPERATE = "COOPERATE"
    OBSERVE = "OBSERVE"


@dataclass(frozen=True)
class RelationshipEvent:
    event_id: str
    character_a: str
    character_b: str
    event_type: RelationshipEventType
    timestamp: str = ""
    source_event_id: str = ""
    metadata: Mapping = None

    def __post_init__(self):
        for name in ("event_id", "character_a", "character_b"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must not be empty.")
        if self.character_a == self.character_b:
            raise ValueError("relationship participants must be different.")
        kind = self.event_type if isinstance(self.event_type, RelationshipEventType) else RelationshipEventType(self.event_type)
        object.__setattr__(self, "event_type", kind)
        if not isinstance(self.timestamp, str) or not isinstance(self.source_event_id, str):
            raise TypeError("timestamp and source_event_id must be strings.")
        if self.metadata is None:
            object.__setattr__(self, "metadata", MappingProxyType({}))
        elif not isinstance(self.metadata, Mapping):
            raise TypeError("metadata must be a mapping.")
        else:
            object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))
