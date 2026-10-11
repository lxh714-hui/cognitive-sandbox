from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class InteractionReaction:
    interaction_id: str
    agent_id: str
    reaction_type: str
    description: str

    def __post_init__(self) -> None:
        for name in ("interaction_id", "agent_id", "reaction_type", "description"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must not be empty.")
