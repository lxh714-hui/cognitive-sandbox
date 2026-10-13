from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class EventListener:
    """A named callback registered in deterministic subscription order."""

    name: str
    callback: Callable[[Any, Any], Any]
    event_types: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("listener name must not be empty.")
        if not callable(self.callback):
            raise TypeError("listener callback must be callable.")
        object.__setattr__(self, "event_types", tuple(self.event_types))

    def accepts(self, event) -> bool:
        return not self.event_types or event.event_type in self.event_types
