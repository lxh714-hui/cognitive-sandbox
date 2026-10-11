from __future__ import annotations

from collections.abc import Iterable

from cognitive_sandbox.domain.agent_state import AgentDynamicState
from cognitive_sandbox.domain.character import CharacterState
from cognitive_sandbox.domain.character_development import CharacterDevelopmentState
from cognitive_sandbox.domain.memory import InitialMemory


class CharacterGrowthEngine:
    """Summarize deterministic growth signals from a character's memories."""

    def evaluate(
        self,
        character_state: CharacterState,
        memories: Iterable[InitialMemory],
        dynamic_state: AgentDynamicState,
    ) -> CharacterDevelopmentState:
        if not isinstance(character_state, CharacterState):
            raise TypeError("character_state must be a CharacterState.")
        if isinstance(memories, (str, bytes)):
            raise TypeError("memories must be a collection of InitialMemory values.")
        memory_items = tuple(memories)
        if any(not isinstance(memory, InitialMemory) for memory in memory_items):
            raise TypeError("memories must contain only InitialMemory values.")
        if not isinstance(dynamic_state, AgentDynamicState):
            raise TypeError("dynamic_state must be an AgentDynamicState.")
        if dynamic_state.character_id != character_state.character_id:
            raise ValueError("dynamic_state.character_id must match character_state.character_id.")

        traits: list[str] = []
        values: list[str] = []
        for memory in memory_items:
            if "帮助" in memory.content:
                self._append_once(traits, "compassion_strengthened")
                self._append_once(values, "helping_others")
            if "保护" in memory.content:
                self._append_once(traits, "protective")
                self._append_once(values, "responsibility")
            if "失败" in memory.content:
                self._append_once(traits, "resilience")

        return CharacterDevelopmentState(
            character_id=character_state.character_id,
            trait_growth=tuple(traits),
            value_growth=tuple(values),
            experience_count=len(memory_items),
        )

    @staticmethod
    def _append_once(items: list[str], value: str) -> None:
        if value not in items:
            items.append(value)
