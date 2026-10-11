from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PlayerAction:
    player_id: str
    raw_input: str
    intent: str
    target: str | None = None

    def __post_init__(self) -> None:
        for name in ("player_id", "raw_input", "intent"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must not be empty.")
        if self.target is not None and (
            not isinstance(self.target, str) or not self.target.strip()
        ):
            raise ValueError("target must be None or a non-empty string.")
