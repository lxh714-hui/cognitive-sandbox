from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class DevelopmentChangeType(str, Enum):
    BELIEF_SHIFT = "belief_shift"
    EMOTION_TENDENCY = "emotion_tendency"
    COGNITIVE_TENDENCY = "cognitive_tendency"
    BEHAVIOR_TENDENCY = "behavior_tendency"


@dataclass(frozen=True)
class DevelopmentRecord:
    character_id: str
    source_event: str
    change_type: DevelopmentChangeType
    before: str
    after: str
    reason: str

    def __post_init__(self):
        for key in ("character_id", "source_event", "before", "after", "reason"):
            if not isinstance(getattr(self, key), str) or not getattr(self, key).strip():
                raise ValueError(f"{key} must not be empty.")
        if not isinstance(self.change_type, DevelopmentChangeType):
            object.__setattr__(self, "change_type", DevelopmentChangeType(self.change_type))
