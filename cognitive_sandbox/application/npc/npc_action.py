from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise TypeError("parameters keys must be strings.")
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(_freeze(item) for item in value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError("parameters must contain only JSON-compatible values.")


@dataclass(frozen=True)
class NpcAction:
    """A deterministic candidate response; it does not itself mutate the world."""

    actor_id: str
    action_type: str
    target: str | None = None
    parameters: Mapping[str, Any] = field(default_factory=dict)
    reason: str = ""

    def __post_init__(self) -> None:
        for name in ("actor_id", "action_type"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must not be empty.")
        if self.target is not None and (not isinstance(self.target, str) or not self.target.strip()):
            raise ValueError("target must be None or a non-empty string.")
        if not isinstance(self.reason, str) or not self.reason.strip():
            raise ValueError("reason must not be empty.")
        if not isinstance(self.parameters, Mapping):
            raise TypeError("parameters must be a mapping.")
        object.__setattr__(self, "parameters", _freeze(self.parameters))
