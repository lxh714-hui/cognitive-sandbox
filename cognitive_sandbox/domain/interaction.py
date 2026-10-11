from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AgentInteraction:
    interaction_id: str
    source_agent_id: str
    target_agent_id: str
    interaction_type: str
    description: str

    def __post_init__(self) -> None:
        for name in (
            "interaction_id",
            "source_agent_id",
            "target_agent_id",
            "interaction_type",
            "description",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must not be empty.")
