from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from cognitive_sandbox.domain.agent_context import AgentContext
from cognitive_sandbox.domain.interaction import AgentInteraction


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
class InteractionSimulationResult:
    interactions: tuple[AgentInteraction, ...]
    agent_contexts: tuple[AgentContext, ...]
    world_state: Mapping[str, Any]

    def __post_init__(self) -> None:
        if isinstance(self.interactions, (str, bytes)):
            raise TypeError("interactions must contain AgentInteraction values.")
        interactions = tuple(self.interactions)
        if any(not isinstance(item, AgentInteraction) for item in interactions):
            raise TypeError("interactions must contain only AgentInteraction values.")
        if isinstance(self.agent_contexts, (str, bytes)):
            raise TypeError("agent_contexts must contain AgentContext values.")
        contexts = tuple(self.agent_contexts)
        if any(not isinstance(item, AgentContext) for item in contexts):
            raise TypeError("agent_contexts must contain only AgentContext values.")
        if not isinstance(self.world_state, Mapping):
            raise TypeError("world_state must be a mapping.")
        object.__setattr__(self, "interactions", interactions)
        object.__setattr__(self, "agent_contexts", contexts)
        object.__setattr__(self, "world_state", _freeze(self.world_state))
