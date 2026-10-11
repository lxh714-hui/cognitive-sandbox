from __future__ import annotations

from dataclasses import dataclass

from cognitive_sandbox.domain.agent_context import AgentContext
from cognitive_sandbox.domain.world_state import WorldState


@dataclass(frozen=True)
class BootstrapResult:
    world_state: WorldState
    agent_contexts: tuple[AgentContext, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.world_state, WorldState):
            raise TypeError("world_state must be a WorldState.")
        contexts = tuple(self.agent_contexts)
        if any(not isinstance(context, AgentContext) for context in contexts):
            raise TypeError("agent_contexts must contain AgentContext values.")
        object.__setattr__(self, "agent_contexts", contexts)
