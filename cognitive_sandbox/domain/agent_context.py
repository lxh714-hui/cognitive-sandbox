from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from cognitive_sandbox.domain.agent_state import AgentDynamicState
from cognitive_sandbox.domain.character import CharacterState
from cognitive_sandbox.domain.memory import InitialMemory
from cognitive_sandbox.domain.relationship import RelationshipState


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise TypeError("world_state keys must be strings.")
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, set):
        return frozenset(_freeze(item) for item in value)
    return value


@dataclass(frozen=True)
class AgentContext:
    character_id: str
    character_state: CharacterState
    memories: tuple[InitialMemory, ...]
    relationships: tuple[RelationshipState, ...]
    world_state: dict[str, Any]
    dynamic_state: AgentDynamicState | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.character_id, str) or not self.character_id.strip():
            raise ValueError("character_id must not be empty.")
        if not isinstance(self.character_state, CharacterState):
            raise TypeError("character_state must be a CharacterState.")
        if self.character_id != self.character_state.character_id:
            raise ValueError("character_id must match character_state.character_id.")
        dynamic_state = self.dynamic_state or AgentDynamicState(
            character_id=self.character_id,
            confidence=0.5,
            stress=0.0,
            motivation=0.5,
        )
        if not isinstance(dynamic_state, AgentDynamicState):
            raise TypeError("dynamic_state must be an AgentDynamicState.")
        if dynamic_state.character_id != self.character_id:
            raise ValueError("dynamic_state.character_id must match character_id.")

        if isinstance(self.memories, (str, bytes)):
            raise TypeError("memories must be a collection of InitialMemory values.")
        memories = tuple(self.memories)
        if any(not isinstance(memory, InitialMemory) for memory in memories):
            raise TypeError("memories must contain only InitialMemory values.")
        if isinstance(self.relationships, (str, bytes)):
            raise TypeError("relationships must be a collection of RelationshipState values.")
        relationships = tuple(self.relationships)
        if any(not isinstance(item, RelationshipState) for item in relationships):
            raise TypeError("relationships must contain only RelationshipState values.")
        if not isinstance(self.world_state, Mapping):
            raise TypeError("world_state must be a mapping.")

        object.__setattr__(self, "memories", memories)
        object.__setattr__(self, "relationships", relationships)
        object.__setattr__(self, "world_state", _freeze(self.world_state))
        object.__setattr__(self, "dynamic_state", dynamic_state)
