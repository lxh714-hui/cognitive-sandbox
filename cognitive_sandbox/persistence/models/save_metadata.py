from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SaveMetadata:
    instance_id: str
    world_id: str
    scenario_id: str
    name: str
    description: str
    created_time: str
    last_played_time: str
    status: str = "可继续"
    world_status: str = "暂无状态摘要"
    player_character_id: str | None = None

    def __post_init__(self) -> None:
        for field_name in (
            "instance_id", "world_id", "scenario_id", "name", "description",
            "created_time", "last_played_time", "status", "world_status",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must not be empty.")
        if self.player_character_id is not None and (
            not isinstance(self.player_character_id, str) or not self.player_character_id.strip()
        ):
            raise ValueError("player_character_id must be a non-empty string or None.")
