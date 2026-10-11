from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Protocol

from cognitive_sandbox.application.action_resolver import ActionResolver
from cognitive_sandbox.application.runtime_coordinator import RuntimeCoordinator
from cognitive_sandbox.domain.actions import ActionProposal
from cognitive_sandbox.domain.observations import PerceptionContext
from cognitive_sandbox.domain.simulation import SimulationStepResult
from cognitive_sandbox.domain.world_events import WorldEvent


class EventCoordinator(Protocol):
    def process_event(
        self,
        world_event: WorldEvent,
        agent_ids: Sequence[str],
        perception_contexts: Mapping[str, PerceptionContext],
    ) -> list[ActionProposal]: ...


class SimulationRuntime:
    """Advance one discrete processing step without executing resolved actions."""

    def __init__(
        self,
        coordinator: EventCoordinator,
        action_resolver: ActionResolver,
    ) -> None:
        self._coordinator = coordinator
        self._action_resolver = action_resolver

    def process_event(
        self,
        world_event: WorldEvent,
        agent_ids: Sequence[str],
        perception_contexts: Mapping[str, PerceptionContext],
    ) -> SimulationStepResult:
        if not isinstance(world_event, WorldEvent):
            raise TypeError("world_event must be a WorldEvent.")
        proposals = self._coordinator.process_event(
            world_event,
            agent_ids,
            perception_contexts,
        )
        resolved_actions = self._action_resolver.resolve(
            proposals,
            current_world_revision=world_event.world_revision,
        )
        return SimulationStepResult(
            world_event_id=world_event.event_id,
            proposals=tuple(proposals),
            resolved_actions=tuple(resolved_actions),
        )
