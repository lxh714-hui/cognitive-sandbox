from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from cognitive_sandbox.application.action_decision import ActionDecisionInput
from cognitive_sandbox.domain.actions import ActionCandidate, ResolvedActionResult
from cognitive_sandbox.domain.agent_context import AgentContext
from cognitive_sandbox.domain.simulation_result import SimulationTickResult
from cognitive_sandbox.domain.world_events import WorldEvent
from cognitive_sandbox.domain.world_transition import WorldStateTransition


class SimulationTick:
    """Coordinate one deterministic agent action and its state updates."""

    def __init__(
        self,
        decision_engine: Any,
        action_resolver: Any,
        action_event_adapter: Any,
        world_state_updater: Any,
        world_state_applier: Any,
        memory_updater: Any,
        relationship_updater: Any,
        agent_state_updater: Any,
        agent_context_builder: Any,
    ) -> None:
        self._decision_engine = decision_engine
        self._action_resolver = action_resolver
        self._action_event_adapter = action_event_adapter
        self._world_state_updater = world_state_updater
        self._world_state_applier = world_state_applier
        self._memory_updater = memory_updater
        self._relationship_updater = relationship_updater
        self._agent_state_updater = agent_state_updater
        self._agent_context_builder = agent_context_builder

    def run(
        self,
        agent_context: AgentContext,
        world_state: Mapping[str, Any],
        situation: str,
    ) -> SimulationTickResult:
        if not isinstance(agent_context, AgentContext):
            raise TypeError("agent_context must be an AgentContext.")
        if not isinstance(world_state, Mapping):
            raise TypeError("world_state must be a mapping.")
        decision_input = ActionDecisionInput(agent_context, situation)
        candidates = tuple(self._decision_engine.generate(decision_input))
        if any(not isinstance(candidate, ActionCandidate) for candidate in candidates):
            raise TypeError("decision_engine must return ActionCandidate values.")
        if not candidates:
            return SimulationTickResult(world_state, agent_context, ())

        action = candidates[0]
        resolved = self._action_resolver.resolve(action, world_state)
        if not isinstance(resolved, ResolvedActionResult):
            raise TypeError("action_resolver must return a ResolvedActionResult.")
        event = self._action_event_adapter.adapt(resolved, action)
        if not isinstance(event, WorldEvent):
            raise TypeError("action_event_adapter must return a WorldEvent.")

        transition = self._world_state_updater.update(event, world_state)
        if not isinstance(transition, WorldStateTransition):
            raise TypeError("world_state_updater must return a WorldStateTransition.")
        updated_world_state = self._world_state_applier.apply(world_state, transition)
        memories = self._memory_updater.update(agent_context, event)
        relationships = self._relationship_updater.update(agent_context.relationships, event)
        dynamic_state = self._agent_state_updater.update(agent_context.dynamic_state, event)
        updated_context = self._agent_context_builder.build(
            agent_context.character_state,
            memories,
            relationships,
            updated_world_state,
            dynamic_state=dynamic_state,
        )

        return SimulationTickResult(updated_world_state, updated_context, (event,), action=action)
