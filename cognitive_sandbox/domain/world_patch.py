from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from cognitive_sandbox.domain.character_card import CharacterCard
from cognitive_sandbox.domain.event_card import EventCard


class WorldPatchType(str, Enum):
    CHARACTER_ADDITION = "CHARACTER_ADDITION"
    LORE_PATCH = "LORE_PATCH"
    EVENT_ADDITION = "EVENT_ADDITION"


@dataclass(frozen=True)
class CharacterAddition:
    character_card: CharacterCard
    introduction_method: str
    appearance_condition: str
    entry_event: str

    def __post_init__(self) -> None:
        if not isinstance(self.character_card, CharacterCard):
            raise TypeError("character_card must be a CharacterCard.")
        for field_name in ("introduction_method", "appearance_condition", "entry_event"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must not be empty.")


@dataclass(frozen=True)
class WorldPatch:
    id: str
    type: WorldPatchType
    title: str
    description: str
    created_at: str
    effective_time: str
    source: str
    payload: object | None = None

    def __post_init__(self) -> None:
        for field_name in ("id", "title", "description", "created_at", "effective_time", "source"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must not be empty.")
        if not isinstance(self.type, WorldPatchType):
            raise TypeError("type must be a WorldPatchType.")
        if self.type is WorldPatchType.CHARACTER_ADDITION and not isinstance(self.payload, CharacterAddition):
            raise TypeError("CHARACTER_ADDITION patches require a CharacterAddition payload.")
        if self.type is WorldPatchType.EVENT_ADDITION and not isinstance(self.payload, EventCard):
            raise TypeError("EVENT_ADDITION patches require an EventCard payload.")
        if self.type is WorldPatchType.LORE_PATCH and not isinstance(self.payload, str):
            raise TypeError("LORE_PATCH patches require a string payload.")
        if isinstance(self.payload, str) and not self.payload.strip():
            raise ValueError("payload must not be empty.")
