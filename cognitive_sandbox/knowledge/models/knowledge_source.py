from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class KnowledgeSource:
    """Provenance for a character's knowledge record."""

    source_id: str
    source_type: str
    description: str
    actor_id: str | None = None

    def __post_init__(self) -> None:
        for name in ("source_id", "source_type", "description"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must not be empty.")
        if self.actor_id is not None and (not isinstance(self.actor_id, str) or not self.actor_id.strip()):
            raise ValueError("actor_id must be a non-empty string or None.")
