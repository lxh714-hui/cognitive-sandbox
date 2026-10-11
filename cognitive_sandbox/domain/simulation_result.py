from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from cognitive_sandbox.domain.agent_context import AgentContext
from cognitive_sandbox.domain.actions import ActionCandidate
from cognitive_sandbox.domain.world_events import WorldEvent


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise TypeError("world_state keys must be strings.")
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(_freeze(item) for item in value)
    return value


@dataclass(frozen=True)
class SimulationTickResult:
    world_state: Mapping[str, Any]
    agent_context: AgentContext
    events: tuple[WorldEvent, ...]
    action: ActionCandidate | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.world_state, Mapping):
            raise TypeError("world_state must be a mapping.")
        if not isinstance(self.agent_context, AgentContext):
            raise TypeError("agent_context must be an AgentContext.")
        if self.action is not None and not isinstance(self.action, ActionCandidate):
            raise TypeError("action must be an ActionCandidate or None.")
        if isinstance(self.events, (str, bytes)):
            raise TypeError("events must be a collection of WorldEvent values.")
        events = tuple(self.events)
        if any(not isinstance(event, WorldEvent) for event in events):
            raise TypeError("events must contain only WorldEvent values.")
        object.__setattr__(self, "world_state", _freeze(self.world_state))
        object.__setattr__(self, "events", events)
