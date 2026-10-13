from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise TypeError("parameters mapping keys must be strings.")
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, (tuple, list)):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(_freeze(item) for item in value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError("parameters must contain only JSON-compatible values.")


@dataclass(frozen=True)
class ActionIntent:
    """Open-vocabulary, read-only interpretation of one player action."""

    actor_id: str
    raw_input: str
    intent: str
    target: str | None = None
    object: str | None = None
    parameters: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for field_name in ("actor_id", "raw_input", "intent"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must not be empty.")
        for field_name in ("target", "object"):
            value = getattr(self, field_name)
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise ValueError(f"{field_name} must be None or a non-empty string.")
        parameters = self.parameters if self.parameters is not None else {}
        if not isinstance(parameters, Mapping):
            raise TypeError("parameters must be a mapping.")
        object.__setattr__(self, "parameters", _freeze(parameters))
