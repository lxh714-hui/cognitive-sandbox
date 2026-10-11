from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from typing import Protocol
from uuid import uuid4

from cognitive_sandbox.domain.cognition import AgentCognitiveState, LongTermMemory


class CognitiveStateReader(Protocol):
    def get_state(self, agent_id: str) -> AgentCognitiveState: ...


class LongTermMemoryStore(Protocol):
    def list_long_term_memories(self, agent_id: str) -> list[LongTermMemory]: ...
    def append_long_term_memory(self, memory: LongTermMemory) -> bool: ...


class MemoryEncoder:
    """Encode salient, agent-owned observations from working memory."""

    def __init__(
        self,
        cognitive_state_reader: CognitiveStateReader,
        memory_store: LongTermMemoryStore,
        *,
        salience_threshold: float = 0.75,
        id_factory: Callable[[], str] | None = None,
        clock: Callable[[], str] | None = None,
    ) -> None:
        if isinstance(salience_threshold, bool) or not isinstance(salience_threshold, (int, float)):
            raise TypeError("salience_threshold must be a number between 0 and 1.")
        if not 0 <= salience_threshold <= 1:
            raise ValueError("salience_threshold must be between 0 and 1.")
        self._cognitive_state_reader = cognitive_state_reader
        self._memory_store = memory_store
        self._salience_threshold = float(salience_threshold)
        self._id_factory = id_factory or (lambda: str(uuid4()))
        self._clock = clock or (lambda: datetime.now(timezone.utc).isoformat())

    def encode(self, agent_id: str) -> list[LongTermMemory]:
        """Encode eligible working-memory observations for only the requested agent."""
        if not isinstance(agent_id, str) or not agent_id.strip():
            raise ValueError("agent_id must not be empty.")
        state = self._cognitive_state_reader.get_state(agent_id)
        if state.agent_id != agent_id:
            raise ValueError("Cognitive state reader returned another agent's state.")

        existing_sources = {
            source_ref
            for memory in self._memory_store.list_long_term_memories(agent_id)
            for source_ref in memory.source_refs
        }
        encoded: list[LongTermMemory] = []
        for item in state.working_memory:
            observation_id = item.content.get("observation_id")
            # Working-memory source_refs are the provenance authority. Never promote its
            # source_event_ids field into memory or accept an event ID as the memory source.
            if (
                item.agent_id != agent_id
                or not isinstance(observation_id, str)
                or not observation_id.strip()
                or item.source_refs != (observation_id,)
                or observation_id in existing_sources
            ):
                continue

            emotion_relevant = observation_id in state.emotion_state.source_refs
            salience = min(1.0, item.priority * 0.7 + (0.3 if emotion_relevant else 0.0))
            if salience < self._salience_threshold:
                continue

            content = {
                "observation_id": observation_id,
                "text": item.content.get("text", ""),
                "channel": item.content.get("channel", ""),
                "uncertainty": item.content.get("uncertainty", 1.0),
            }
            memory = LongTermMemory(
                memory_id=self._id_factory(),
                agent_id=agent_id,
                memory_type="episodic",
                content=content,
                source_refs=(observation_id,),
                salience=salience,
                created_at=self._clock(),
            )
            if self._memory_store.append_long_term_memory(memory):
                encoded.append(memory)
                existing_sources.add(observation_id)
        return encoded
