from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise TypeError("metadata keys must be strings.")
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, (tuple, list)):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(_freeze(item) for item in value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError("metadata must contain JSON-compatible values.")


@dataclass(frozen=True)
class WorldEventRecord:
    event_id: str
    event_type: str
    timestamp: str
    actor_ids: tuple[str, ...] = ()
    target_ids: tuple[str, ...] = ()
    location: str | None = None
    importance: float = 0.5
    metadata: Mapping[str, Any] = None

    def __post_init__(self) -> None:
        for field_name in ("event_id", "event_type", "timestamp"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must not be empty.")
        for field_name in ("actor_ids", "target_ids"):
            values = getattr(self, field_name)
            if isinstance(values, (str, bytes)):
                raise TypeError(f"{field_name} must be a collection of IDs.")
            values = tuple(values)
            if any(not isinstance(value, str) or not value.strip() for value in values):
                raise ValueError(f"{field_name} must contain non-empty IDs.")
            object.__setattr__(self, field_name, tuple(dict.fromkeys(values)))
        if self.location is not None and (not isinstance(self.location, str) or not self.location.strip()):
            raise ValueError("location must be None or a non-empty string.")
        if isinstance(self.importance, bool) or not isinstance(self.importance, (int, float)):
            raise TypeError("importance must be a number between 0 and 1.")
        if not 0 <= self.importance <= 1:
            raise ValueError("importance must be between 0 and 1.")
        metadata = {} if self.metadata is None else self.metadata
        if not isinstance(metadata, Mapping):
            raise TypeError("metadata must be a mapping.")
        object.__setattr__(self, "metadata", _freeze(metadata))
        object.__setattr__(self, "importance", float(self.importance))

    @classmethod
    def from_world_event(cls, event, *, timestamp: str | None = None):
        payload = getattr(event, "payload", {})
        metadata = getattr(event, "metadata", None)
        merged = dict(payload) if isinstance(payload, Mapping) else {}
        if isinstance(metadata, Mapping):
            merged.update(metadata)
        importance = merged.pop("importance", 0.5)
        if isinstance(importance, str):
            importance = {"low": 0.2, "medium": 0.5, "high": 0.8}.get(importance.casefold(), 0.5)
        actor_ids = (event.actor_id,) if getattr(event, "actor_id", None) else ()
        target = getattr(event, "target_id", None) or merged.get("target_id")
        targets = (target,) if isinstance(target, str) and target.strip() else ()
        location = getattr(event, "location", None) or merged.get("location")
        created = getattr(event, "timestamp", None) or timestamp
        if not isinstance(created, str) or not created.strip():
            raise ValueError("a timestamp is required to record a world event.")
        return cls(
            event_id=event.event_id,
            event_type=event.event_type,
            timestamp=created,
            actor_ids=actor_ids,
            target_ids=targets,
            location=location if isinstance(location, str) else None,
            importance=importance,
            metadata=merged,
        )
