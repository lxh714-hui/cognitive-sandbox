from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class PresenceState(str, Enum):
    UNKNOWN = "UNKNOWN"
    AVAILABLE = "AVAILABLE"
    INTRODUCED = "INTRODUCED"
    ACTIVE = "ACTIVE"
    LEFT = "LEFT"


@dataclass(frozen=True)
class CharacterPresence:
    character_id: str
    current_location: str | None = None
    availability: PresenceState = PresenceState.UNKNOWN
    introduction_state: PresenceState = PresenceState.UNKNOWN
    entry_conditions: tuple[str, ...] = ()

    def __post_init__(self):
        if not isinstance(self.character_id, str) or not self.character_id.strip():
            raise ValueError("character_id must not be empty.")
        if self.current_location is not None and (not isinstance(self.current_location, str) or not self.current_location.strip()):
            raise ValueError("current_location must be None or non-empty.")
        for field in ("availability", "introduction_state"):
            value = getattr(self, field)
            if not isinstance(value, PresenceState):
                try:
                    object.__setattr__(self, field, PresenceState(value))
                except (TypeError, ValueError) as error:
                    raise ValueError(f"{field} must be a PresenceState.") from error
        conditions = tuple(self.entry_conditions)
        if any(not isinstance(item, str) or not item.strip() for item in conditions):
            raise ValueError("entry_conditions must contain non-empty strings.")
        object.__setattr__(self, "entry_conditions", conditions)
