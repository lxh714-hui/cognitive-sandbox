from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from cognitive_sandbox.domain.agent_context import AgentContext
from cognitive_sandbox.domain.interaction import AgentInteraction
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
class MultiAgentSimulationResult:
    world_state: Mapping[str, Any]
    agent_contexts: tuple[AgentContext, ...]
    events: tuple[WorldEvent, ...]
    interactions: tuple[AgentInteraction, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.world_state, Mapping):
            raise TypeError("world_state must be a mapping.")
        if isinstance(self.agent_contexts, (str, bytes)):
            raise TypeError("agent_contexts must contain AgentContext values.")
        agent_contexts = tuple(self.agent_contexts)
        if any(not isinstance(context, AgentContext) for context in agent_contexts):
            raise TypeError("agent_contexts must contain only AgentContext values.")
        if isinstance(self.events, (str, bytes)):
            raise TypeError("events must contain WorldEvent values.")
        events = tuple(self.events)
        if any(not isinstance(event, WorldEvent) for event in events):
            raise TypeError("events must contain only WorldEvent values.")
        if isinstance(self.interactions, (str, bytes)):
            raise TypeError("interactions must contain AgentInteraction values.")
        interactions = tuple(self.interactions)
        if any(not isinstance(item, AgentInteraction) for item in interactions):
            raise TypeError("interactions must contain only AgentInteraction values.")
        object.__setattr__(self, "world_state", _freeze(self.world_state))
        object.__setattr__(self, "agent_contexts", agent_contexts)
        object.__setattr__(self, "events", events)
        object.__setattr__(self, "interactions", interactions)
