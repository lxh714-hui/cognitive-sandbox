from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from cognitive_sandbox.domain.agent_context import AgentContext
from cognitive_sandbox.domain.agent_state import AgentDynamicState
from cognitive_sandbox.domain.character import CharacterState
from cognitive_sandbox.domain.memory import InitialMemory
from cognitive_sandbox.domain.relationship import RelationshipState


class AgentContextBuilder:
    """Assemble already-created agent and world data without interpreting it."""

    def build(
        self,
        character_state: CharacterState,
        memories: Iterable[InitialMemory],
        relationships: Iterable[RelationshipState],
        world_state: Mapping[str, Any],
        *,
        dynamic_state: AgentDynamicState | None = None,
    ) -> AgentContext:
        if not isinstance(character_state, CharacterState):
            raise TypeError("character_state must be a CharacterState.")
        if isinstance(memories, (str, bytes)):
            raise TypeError("memories must be a collection of InitialMemory values.")
        if isinstance(relationships, (str, bytes)):
            raise TypeError("relationships must be a collection of RelationshipState values.")
        if not isinstance(world_state, Mapping):
            raise TypeError("world_state must be a mapping.")
        if dynamic_state is not None and not isinstance(dynamic_state, AgentDynamicState):
            raise TypeError("dynamic_state must be an AgentDynamicState or None.")
        if dynamic_state is None:
            dynamic_state = AgentDynamicState(character_state.character_id, 0.5, 0.0, 0.5)

        return AgentContext(
            character_id=character_state.character_id,
            character_state=character_state,
            memories=tuple(memories),
            relationships=tuple(relationships),
            world_state=world_state,
            dynamic_state=dynamic_state,
        )
