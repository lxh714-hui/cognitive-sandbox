from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class PlayerIntent:
    """Structured, validated interpretation of one player's input."""

    player_id: str
    raw_input: str
    intent: str
    target: str | None = None

    SUPPORTED_INTENTS: ClassVar[frozenset[str]] = frozenset({"observe", "help", "protect"})

    def __post_init__(self) -> None:
        for name in ("player_id", "raw_input"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must not be empty.")
        if not isinstance(self.intent, str) or self.intent not in self.SUPPORTED_INTENTS:
            raise ValueError("intent must be observe, help, or protect.")
        if self.target is not None and (
            not isinstance(self.target, str) or not self.target.strip()
        ):
            raise ValueError("target must be None or a non-empty string.")
