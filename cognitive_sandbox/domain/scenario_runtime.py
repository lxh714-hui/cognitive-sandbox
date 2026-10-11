from __future__ import annotations

from dataclasses import dataclass

from cognitive_sandbox.domain.agent_context import AgentContext
from cognitive_sandbox.domain.constraint import Constraint
from cognitive_sandbox.domain.event_card import EventCard
from cognitive_sandbox.domain.world_state import WorldState


@dataclass(frozen=True)
class AgentRuntimeProfile:
    """Runtime context plus static constraints carried from its character card."""

    agent_context: AgentContext
    constraints: tuple[Constraint, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.agent_context, AgentContext):
            raise TypeError("agent_context must be an AgentContext.")
        if isinstance(self.constraints, (str, bytes)):
            raise TypeError("constraints must be a collection of Constraint values.")
        constraints = tuple(self.constraints)
        if any(not isinstance(item, Constraint) for item in constraints):
            raise TypeError("constraints must contain only Constraint values.")
        object.__setattr__(self, "constraints", constraints)

    @property
    def agent_id(self) -> str:
        return self.agent_context.character_id


@dataclass(frozen=True)
class ScenarioRuntime:
    """Complete content-backed runtime objects, not yet advanced by simulation."""

    scenario_id: str
    world_state: WorldState
    agents: tuple[AgentRuntimeProfile, ...]
    initial_events: tuple[EventCard, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.scenario_id, str) or not self.scenario_id.strip():
            raise ValueError("scenario_id must not be empty.")
        if not isinstance(self.world_state, WorldState):
            raise TypeError("world_state must be a WorldState.")
        agents = tuple(self.agents)
        events = tuple(self.initial_events)
        if any(not isinstance(agent, AgentRuntimeProfile) for agent in agents):
            raise TypeError("agents must contain AgentRuntimeProfile values.")
        if any(not isinstance(event, EventCard) for event in events):
            raise TypeError("initial_events must contain EventCard values.")
        object.__setattr__(self, "agents", agents)
        object.__setattr__(self, "initial_events", events)

    @property
    def agent_contexts(self) -> tuple[AgentContext, ...]:
        return tuple(agent.agent_context for agent in self.agents)
