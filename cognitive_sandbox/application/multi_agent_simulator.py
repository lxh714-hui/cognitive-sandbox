from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from cognitive_sandbox.application.interaction_manager import InteractionManager
from cognitive_sandbox.application.interaction_resolver import InteractionResolver
from cognitive_sandbox.domain.agent_context import AgentContext
from cognitive_sandbox.domain.interaction_result import InteractionSimulationResult
from cognitive_sandbox.domain.multi_agent_result import MultiAgentSimulationResult
from cognitive_sandbox.domain.simulation_result import SimulationTickResult


class MultiAgentSimulator:
    """Run the shared single-agent tick sequentially for each agent."""

    def __init__(self, simulation_tick: Any, interaction_manager: InteractionManager | None = None) -> None:
        if not callable(getattr(simulation_tick, "run", None)):
            raise TypeError("simulation_tick must provide a callable run method.")
        self._simulation_tick = simulation_tick
        if interaction_manager is not None and not callable(getattr(interaction_manager, "generate", None)):
            raise TypeError("interaction_manager must provide a callable generate method.")
        self._interaction_manager = interaction_manager or InteractionManager(InteractionResolver())

    def run(
        self,
        agent_contexts: Iterable[AgentContext],
        world_state: Mapping[str, Any],
        situation: str,
    ) -> MultiAgentSimulationResult:
        if isinstance(agent_contexts, (str, bytes)):
            raise TypeError("agent_contexts must be a collection of AgentContext values.")
        contexts = tuple(agent_contexts)
        if any(not isinstance(context, AgentContext) for context in contexts):
            raise TypeError("agent_contexts must contain only AgentContext values.")
        if not isinstance(world_state, Mapping):
            raise TypeError("world_state must be a mapping.")
        if not isinstance(situation, str) or not situation.strip():
            raise ValueError("situation must not be empty.")

        current_world_state = world_state
        updated_contexts: list[AgentContext] = []
        events = []
        actions = []
        for context in contexts:
            tick_result = self._simulation_tick.run(context, current_world_state, situation)
            if not isinstance(tick_result, SimulationTickResult):
                raise TypeError("simulation_tick.run must return a SimulationTickResult.")
            current_world_state = tick_result.world_state
            updated_contexts.append(tick_result.agent_context)
            events.extend(tick_result.events)
            if tick_result.action is not None:
                actions.append(tick_result.action)

        interactions = self._interaction_manager.generate(tuple(updated_contexts), tuple(actions))
        interaction_result = InteractionSimulationResult(
            interactions=interactions,
            agent_contexts=tuple(updated_contexts),
            world_state=current_world_state,
        )

        return MultiAgentSimulationResult(
            world_state=interaction_result.world_state,
            agent_contexts=interaction_result.agent_contexts,
            events=tuple(events),
            interactions=interaction_result.interactions,
        )
