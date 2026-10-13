from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CharacterMotivation:
    character_id: str
    public_goal: str = ""
    hidden_goal: str = ""
    core_drive: str = ""
    fear: str = ""
    value_conflict: str = ""
    self_awareness: bool = False

    def __post_init__(self):
        if not isinstance(self.character_id, str) or not self.character_id.strip():
            raise ValueError("character_id must not be empty.")
        for field in ("public_goal", "hidden_goal", "core_drive", "fear", "value_conflict"):
            value = getattr(self, field)
            if not isinstance(value, str):
                raise TypeError(f"{field} must be a string.")
        if not isinstance(self.self_awareness, bool):
            raise TypeError("self_awareness must be bool.")

    def view_for(self, viewer_id: str, *, privileged: bool = False) -> "MotivationView":
        visible_to_self = viewer_id == self.character_id and self.self_awareness
        full = privileged
        return MotivationView(
            self.character_id,
            self.public_goal,
            self.hidden_goal if full or visible_to_self else None,
            self.core_drive if full or visible_to_self else None,
            self.fear if full or visible_to_self else None,
            self.value_conflict if full or visible_to_self else None,
        )


@dataclass(frozen=True)
class MotivationView:
    character_id: str
    public_goal: str
    hidden_goal: str | None = None
    core_drive: str | None = None
    fear: str | None = None
    value_conflict: str | None = None
