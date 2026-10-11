from __future__ import annotations

from collections.abc import Callable
from uuid import uuid4

from cognitive_sandbox.domain.agent_context import AgentContext
from cognitive_sandbox.domain.memory import InitialMemory
from cognitive_sandbox.domain.world_events import WorldEvent


class MemoryUpdater:
    """Append a deterministic event-based experience to an agent's memories."""

    _MEMORIES = {
        "help_attempt": ("我曾经帮助过他人", 0.6),
        "protect_attempt": ("我曾经保护过目标", 0.7),
        "observe_action": ("我曾经观察并收集过信息", 0.3),
        "action_failed": ("我曾经经历过一次失败的行动", 0.5),
    }

    def __init__(self, *, memory_id_factory: Callable[[], str] | None = None) -> None:
        self._memory_id_factory = memory_id_factory or (lambda: f"memory_{uuid4().hex}")

    def update(self, context: AgentContext, event: WorldEvent) -> tuple[InitialMemory, ...]:
        if not isinstance(context, AgentContext):
            raise TypeError("context must be an AgentContext.")
        if not isinstance(event, WorldEvent):
            raise TypeError("event must be a WorldEvent.")

        template = self._MEMORIES.get(event.event_type)
        if template is None:
            return context.memories

        memory_id = self._memory_id_factory()
        if not isinstance(memory_id, str) or not memory_id.strip():
            raise ValueError("memory_id_factory must return a non-empty string.")
        if memory_id in {memory.memory_id for memory in context.memories}:
            raise ValueError("memory_id_factory returned an ID already used by this agent.")

        content, importance = template
        new_memory = InitialMemory(memory_id, content, importance)
        return (*context.memories, new_memory)
