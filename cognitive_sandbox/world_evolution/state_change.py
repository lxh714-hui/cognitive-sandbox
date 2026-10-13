from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise TypeError("state change mappings must use string keys.")
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(_freeze(item) for item in value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError("state change values must be immutable JSON-compatible data.")


@dataclass(frozen=True)
class StateChange:
    target_type: str
    target_id: str
    field: str
    old_value: Any
    new_value: Any
    reason: str
    event_id: str | None = None
    timestamp: str | None = None

    def __post_init__(self):
        for name in ("target_type", "target_id", "field", "reason"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must not be empty.")
        for name in ("event_id", "timestamp"):
            value = getattr(self, name)
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise ValueError(f"{name} must be None or a non-empty string.")
        object.__setattr__(self, "old_value", _freeze(self.old_value))
        object.__setattr__(self, "new_value", _freeze(self.new_value))
