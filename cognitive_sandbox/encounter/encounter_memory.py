from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EncounterMemory:
    character_id: str
    other_character_id: str
    encounter_id: str
    source_event_id: str
    memory_type: str
    created_at: str
    public_description: str

    def __post_init__(self):
        for name in ("character_id", "other_character_id", "encounter_id", "source_event_id",
                     "memory_type", "created_at", "public_description"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must not be empty.")
        if self.character_id == self.other_character_id:
            raise ValueError("encounter memory must reference another character.")


@dataclass(frozen=True)
class EncounterHistoryRecord:
    encounter_id: str
    candidate_id: str
    character_a: str
    character_b: str
    location: str
    timestamp: str
    source_event_ids: tuple[str, ...]
    public_description: str

    def __post_init__(self):
        for name in ("encounter_id", "candidate_id", "character_a", "character_b", "location",
                     "timestamp", "public_description"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must not be empty.")
        object.__setattr__(self, "source_event_ids", tuple(self.source_event_ids))


__all__ = ["EncounterMemory", "EncounterHistoryRecord"]
