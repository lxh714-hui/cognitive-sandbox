from __future__ import annotations

from dataclasses import dataclass

from .development_record import DevelopmentRecord


@dataclass(frozen=True)
class CharacterDevelopment:
    character_id: str
    belief_shifts: tuple[tuple[str, str], ...] = ()
    emotion_tendencies: tuple[tuple[str, float], ...] = ()
    cognitive_tendencies: tuple[tuple[str, float], ...] = ()
    behavior_tendencies: tuple[tuple[str, float], ...] = ()
    records: tuple[DevelopmentRecord, ...] = ()

    def __post_init__(self):
        if not isinstance(self.character_id, str) or not self.character_id.strip():
            raise ValueError("character_id must not be empty.")
        for name in ("belief_shifts", "emotion_tendencies", "cognitive_tendencies", "behavior_tendencies", "records"):
            values = tuple(getattr(self, name))
            object.__setattr__(self, name, values)
        for name in ("belief_shifts", "emotion_tendencies", "cognitive_tendencies", "behavior_tendencies"):
            pairs = tuple(tuple(item) for item in getattr(self, name))
            if any(len(item) != 2 or not isinstance(item[0], str) or not item[0].strip() for item in pairs):
                raise ValueError(f"{name} must contain key/value pairs.")
            if name == "belief_shifts" and any(not isinstance(item[1], str) for item in pairs):
                raise TypeError("belief shifts must contain string values.")
            if name != "belief_shifts" and any(
                isinstance(item[1], bool) or not isinstance(item[1], (int, float)) or not 0 <= item[1] <= 1
                for item in pairs
            ):
                raise ValueError(f"{name} values must be between 0 and 1.")
            object.__setattr__(self, name, pairs)
        if any(not isinstance(item, DevelopmentRecord) for item in self.records):
            raise TypeError("records must contain DevelopmentRecord values.")

    def tendency(self, group: str, key: str, default: float = 0.0) -> float:
        values = dict(getattr(self, group))
        return float(values.get(key, default))
