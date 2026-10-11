from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise TypeError("world state keys must be strings.")
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, set):
        return frozenset(_freeze(item) for item in value)
    return value


@dataclass(frozen=True)
class WorldState:
    world_id: str
    name: str
    state: dict[str, Any]
    description: str = ""
    history: tuple[str, ...] = ()
    rules: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for field_name in ("world_id", "name"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must not be empty.")
        if not isinstance(self.state, Mapping):
            raise TypeError("state must be a mapping.")
        if not isinstance(self.description, str):
            raise TypeError("description must be a string.")
        for field_name in ("history", "rules"):
            values = getattr(self, field_name)
            if isinstance(values, (str, bytes)):
                raise TypeError(f"{field_name} must be a collection of strings.")
            values = tuple(values)
            if any(not isinstance(value, str) or not value.strip() for value in values):
                raise ValueError(f"{field_name} must contain non-empty strings.")
            object.__setattr__(self, field_name, values)
        object.__setattr__(self, "state", _freeze(self.state))
