from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WorldInstance:
    """Identity and library-card metadata for one playthrough of a scenario."""

    instance_id: str
    scenario_id: str
    world_id: str
    name: str
    description: str
    status: str
    world_status: str
    last_played: str
    player_character_id: str | None = None

    def __post_init__(self) -> None:
        for field_name in (
            "instance_id", "scenario_id", "world_id", "name", "description", "status", "last_played"
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must not be empty.")
        if not isinstance(self.world_status, str):
            raise TypeError("world_status must be a string.")
        if self.player_character_id is not None and (
            not isinstance(self.player_character_id, str) or not self.player_character_id.strip()
        ):
            raise ValueError("player_character_id must be a non-empty string or None.")
