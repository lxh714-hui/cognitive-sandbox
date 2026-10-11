from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from cognitive_sandbox.application.agent_context_builder import AgentContextBuilder
from cognitive_sandbox.domain.agent_context import AgentContext


class ContextRefresher:
    """Rebuild an agent context while replacing only its world snapshot."""

    def __init__(self, builder: AgentContextBuilder | None = None) -> None:
        selected = builder or AgentContextBuilder()
        if not callable(getattr(selected, "build", None)):
            raise TypeError("builder must provide build().")
        self._builder = selected

    def refresh(
        self,
        existing: AgentContext,
        new_world_state: Mapping[str, Any],
    ) -> AgentContext:
        if not isinstance(existing, AgentContext):
            raise TypeError("existing must be an AgentContext.")
        if not isinstance(new_world_state, Mapping):
            raise TypeError("new_world_state must be a mapping.")
        return self._builder.build(
            existing.character_state,
            existing.memories,
            existing.relationships,
            new_world_state,
            dynamic_state=existing.dynamic_state,
        )
