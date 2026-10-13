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


@dataclass(frozen=True, init=False)
class WorldEvent:
    """An objective, structured change submitted to a world."""

    event_id: str
    branch_id: str
    world_id: str
    event_type: str
    actor_id: str
    payload: Mapping[str, Any]
    world_revision: int
    # Optional event-log details. Defaults preserve the original positional
    # constructor used by existing simulation and persistence code.
    target_id: str | None = None
    location: str | None = None
    timestamp: str | None = None
    metadata: Mapping[str, Any] | None = None

    def __init__(
        self,
        event_id: str,
        branch_id: str = "main",
        world_id: str = "world",
        event_type: str = "",
        actor_id: str | None = None,
        payload: Mapping[str, Any] | None = None,
        world_revision: int = 0,
        target_id: str | None = None,
        location: str | None = None,
        timestamp: str | None = None,
        metadata: Mapping[str, Any] | None = None,
        *,
        actor: str | None = None,
        target: str | None = None,
    ) -> None:
        """Accept the legacy actor_id/payload form and descriptive aliases."""
        if actor_id is not None and actor is not None and actor_id != actor:
            raise ValueError("actor and actor_id must match when both are provided.")
        if target_id is not None and target is not None and target_id != target:
            raise ValueError("target and target_id must match when both are provided.")
        object.__setattr__(self, "event_id", event_id)
        object.__setattr__(self, "branch_id", branch_id)
        object.__setattr__(self, "world_id", world_id)
        object.__setattr__(self, "event_type", event_type)
        object.__setattr__(self, "actor_id", actor_id if actor_id is not None else actor)
        object.__setattr__(self, "payload", {} if payload is None else payload)
        object.__setattr__(self, "world_revision", world_revision)
        object.__setattr__(self, "target_id", target_id if target_id is not None else target)
        object.__setattr__(self, "location", location)
        object.__setattr__(self, "timestamp", timestamp)
        object.__setattr__(self, "metadata", metadata)
        self.__post_init__()

    def __post_init__(self) -> None:
        for field_name in ("event_id", "branch_id", "world_id", "event_type", "actor_id"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must not be empty.")
        if isinstance(self.world_revision, bool) or not isinstance(self.world_revision, int):
            raise TypeError("world_revision must be an integer.")
        if self.world_revision < 0:
            raise ValueError("world_revision must be non-negative.")
        if not isinstance(self.payload, Mapping):
            raise TypeError("payload must be a mapping of structured event details.")
        object.__setattr__(self, "payload", _freeze_payload(self.payload))
        for field_name in ("target_id", "location", "timestamp"):
            value = getattr(self, field_name)
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise ValueError(f"{field_name} must be None or a non-empty string.")
        metadata = self.metadata
        if metadata is not None and not isinstance(metadata, Mapping):
            raise TypeError("metadata must be a mapping when provided.")
        if metadata is not None:
            object.__setattr__(self, "metadata", _freeze_payload(metadata))

    @property
    def actor(self) -> str:
        """Alias used by event-oriented application code."""
        return self.actor_id

    @property
    def target(self) -> str | None:
        """Alias used by event-oriented application code."""
        return self.target_id
