from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise TypeError("context keys must be strings.")
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(_freeze(item) for item in value)
    return value


@dataclass(frozen=True)
class AIGMRequest:
    request_type: str
    context: Mapping[str, Any]

    def __post_init__(self) -> None:
        if not isinstance(self.request_type, str) or not self.request_type.strip():
            raise ValueError("request_type must not be empty.")
        if not isinstance(self.context, Mapping):
            raise TypeError("context must be a mapping.")
        object.__setattr__(self, "context", _freeze(self.context))


@dataclass(frozen=True)
class AIGMResponse:
    content: str
    success: bool = True
    error: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.content, str):
            raise TypeError("content must be a string.")
        if not isinstance(self.success, bool):
            raise TypeError("success must be a bool.")
        if self.success and not self.content.strip():
            raise ValueError("successful response content must not be empty.")
        if not self.success and (not isinstance(self.error, str) or not self.error.strip()):
            raise ValueError("failed responses require a non-empty error status.")
