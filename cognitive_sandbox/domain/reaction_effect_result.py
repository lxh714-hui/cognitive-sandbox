from __future__ import annotations

from dataclasses import dataclass

from cognitive_sandbox.domain.agent_context import AgentContext
from cognitive_sandbox.domain.memory import InitialMemory


@dataclass(frozen=True)
class ReactionEffectResult:
    agent_context: AgentContext
    memory_added: tuple[InitialMemory, ...]
    relationship_changed: bool
    dynamic_state_changed: bool

    def __post_init__(self) -> None:
        if not isinstance(self.agent_context, AgentContext):
            raise TypeError("agent_context must be an AgentContext.")
        if isinstance(self.memory_added, (str, bytes)):
            raise TypeError("memory_added must contain InitialMemory values.")
        memories = tuple(self.memory_added)
        if any(not isinstance(memory, InitialMemory) for memory in memories):
            raise TypeError("memory_added must contain only InitialMemory values.")
        if not isinstance(self.relationship_changed, bool):
            raise TypeError("relationship_changed must be a boolean.")
        if not isinstance(self.dynamic_state_changed, bool):
            raise TypeError("dynamic_state_changed must be a boolean.")
        object.__setattr__(self, "memory_added", memories)
