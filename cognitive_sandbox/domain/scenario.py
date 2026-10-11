from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise TypeError("scenario mapping keys must be strings.")
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, set):
        return frozenset(_freeze(item) for item in value)
    return value


@dataclass(frozen=True)
class Scenario:
    scenario_id: str
    name: str
    description: str
    initial_world_state: dict[str, Any]
    character_templates: tuple[Mapping[str, Any], ...]

    def __post_init__(self) -> None:
        for field_name in ("scenario_id", "name", "description"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must not be empty.")
        if not isinstance(self.initial_world_state, Mapping):
            raise TypeError("initial_world_state must be a mapping.")
        if isinstance(self.character_templates, (str, bytes)):
            raise TypeError("character_templates must be a collection of mappings.")
        templates = tuple(self.character_templates)
        if any(not isinstance(template, Mapping) for template in templates):
            raise TypeError("character_templates must contain mappings.")
        object.__setattr__(self, "initial_world_state", _freeze(self.initial_world_state))
        object.__setattr__(self, "character_templates", tuple(_freeze(item) for item in templates))
