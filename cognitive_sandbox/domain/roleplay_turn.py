from __future__ import annotations

from dataclasses import dataclass


ROLEPLAY_TURN_STATUSES = frozenset(
    {"waiting_input", "input_ready", "executing", "completed"}
)


@dataclass(frozen=True)
class RoleplayTurn:
    turn_id: str
    player_id: str
    status: str
    player_input: str | None = None

    def __post_init__(self) -> None:
        for name in ("turn_id", "player_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must not be empty.")
        if self.status not in ROLEPLAY_TURN_STATUSES:
            raise ValueError("status is not a supported roleplay turn status.")
        if self.player_input is not None and not isinstance(self.player_input, str):
            raise TypeError("player_input must be a string or None.")
