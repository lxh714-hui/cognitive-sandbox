from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Protocol

from cognitive_sandbox.domain.actions import ActionProposal
from cognitive_sandbox.domain.observations import PerceptionContext
from cognitive_sandbox.domain.world_events import WorldEvent


class AgentEventProcessor(Protocol):
    def process_event(
        self,
        agent_id: str,
        world_event: WorldEvent,
        perception_context: PerceptionContext,
    ) -> ActionProposal | None: ...


class RuntimeCoordinator:
    """Run one committed event through each requested agent runtime in order."""

    def __init__(self, agent_runtime: AgentEventProcessor) -> None:
        self._agent_runtime = agent_runtime

    def process_event(
        self,
        world_event: WorldEvent,
        agent_ids: Sequence[str],
        perception_contexts: Mapping[str, PerceptionContext],
    ) -> list[ActionProposal]:
        if not isinstance(world_event, WorldEvent):
            raise TypeError("world_event must be a WorldEvent.")
        if isinstance(agent_ids, str):
            raise TypeError("agent_ids must be a sequence of agent IDs.")
        agent_ids = tuple(agent_ids)
        if any(not isinstance(agent_id, str) or not agent_id.strip() for agent_id in agent_ids):
            raise ValueError("agent_ids must contain non-empty strings.")
        if len(set(agent_ids)) != len(agent_ids):
            raise ValueError("agent_ids must not contain duplicates.")
        if not isinstance(perception_contexts, Mapping):
            raise TypeError("perception_contexts must map agent IDs to PerceptionContext values.")

        proposals: list[ActionProposal] = []
        for agent_id in agent_ids:
            context = perception_contexts.get(agent_id)
            if not isinstance(context, PerceptionContext):
                raise ValueError(f"Missing perception context for agent {agent_id}.")
            proposal = self._agent_runtime.process_event(agent_id, world_event, context)
            if proposal is not None:
                if not isinstance(proposal, ActionProposal):
                    raise TypeError("Agent runtime must return ActionProposal or None.")
                if proposal.actor_id != agent_id:
                    raise ValueError("Agent runtime returned another agent's action proposal.")
                proposals.append(proposal)
        return proposals
