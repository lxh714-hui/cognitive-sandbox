from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class KnowledgeVisibility:
    """Explicit access controls; records are private to their owner by default."""

    allowed_character_ids: tuple[str, ...] = ()
    public: bool = False

    def __post_init__(self) -> None:
        values = self.allowed_character_ids
        if isinstance(values, (str, bytes)):
            raise TypeError("allowed_character_ids must be a collection of IDs.")
        normalized = tuple(values)
        if any(not isinstance(value, str) or not value.strip() for value in normalized):
            raise ValueError("allowed_character_ids must contain non-empty IDs.")
        if not isinstance(self.public, bool):
            raise TypeError("public must be a boolean.")
        object.__setattr__(self, "allowed_character_ids", normalized)

    def allows(self, character_id: str, owner_id: str) -> bool:
        return self.public or character_id == owner_id or character_id in self.allowed_character_ids
