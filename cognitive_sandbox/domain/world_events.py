from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping


def _freeze_payload(value: Any) -> Any:
    """Recursively freeze structured event details."""
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise TypeError("World event payload keys must be strings.")
        return MappingProxyType({key: _freeze_payload(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_payload(item) for item in value)
    if isinstance(value, set):
        return frozenset(_freeze_payload(item) for item in value)
    return value


@dataclass(frozen=True)
class WorldEvent:
    """An objective, structured change submitted to a world."""

    event_id: str
    branch_id: str
    world_id: str
    event_type: str
    actor_id: str
    payload: Mapping[str, Any]
    world_revision: int

    def __post_init__(self) -> None:
        for field_name in ("event_id", "branch_id", "world_id", "event_type", "actor_id"):
            if not getattr(self, field_name).strip():
                raise ValueError(f"{field_name} must not be empty.")
        if isinstance(self.world_revision, bool) or not isinstance(self.world_revision, int):
            raise TypeError("world_revision must be an integer.")
        if self.world_revision < 0:
            raise ValueError("world_revision must be non-negative.")
        if not isinstance(self.payload, Mapping):
            raise TypeError("payload must be a mapping of structured event details.")
        object.__setattr__(self, "payload", _freeze_payload(self.payload))
