from dataclasses import dataclass
from types import MappingProxyType
from collections.abc import Mapping


@dataclass(frozen=True)
class RelationshipMemory:
    character_a: str
    character_b: str
    source_event: str
    memory_type: str
    impact: Mapping
    time: str = ""

    def __post_init__(self):
        for name in ("character_a", "character_b", "source_event", "memory_type"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must not be empty.")
        if self.character_a == self.character_b:
            raise ValueError("relationship participants must be different.")
        if not isinstance(self.impact, Mapping):
            raise TypeError("impact must be a mapping.")
        object.__setattr__(self, "impact", MappingProxyType(dict(self.impact)))
        if not isinstance(self.time, str):
            raise TypeError("time must be a string.")
