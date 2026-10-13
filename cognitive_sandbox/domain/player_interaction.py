from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any


class InteractionSource(str, Enum):
    TEXT = "TEXT"
    BUTTON = "BUTTON"
    SYSTEM = "SYSTEM"


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise TypeError("parameters keys must be strings")
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, (tuple, list)):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(_freeze(item) for item in value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError("parameters must contain JSON-compatible values")


@dataclass(frozen=True)
class PlayerInteraction:
    """One player-originated or system-originated interaction request."""

    actor_id: str
    intent: str
    source: InteractionSource | str
    raw_input: str = ""
    target: str | None = None
    object: str | None = None
    parameters: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in ("actor_id", "intent"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must not be empty")
        try:
            source = InteractionSource(self.source)
        except ValueError as error:
            raise ValueError("source must be text, button, or system") from error
        if not isinstance(self.raw_input, str):
            raise TypeError("raw_input must be a string")
        for name in ("target", "object"):
            value = getattr(self, name)
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise ValueError(f"{name} must be None or non-empty")
        if not isinstance(self.parameters, Mapping):
            raise TypeError("parameters must be a mapping")
        object.__setattr__(self, "source", source)
        object.__setattr__(self, "raw_input", self.raw_input.strip())
        object.__setattr__(self, "parameters", _freeze(self.parameters))
