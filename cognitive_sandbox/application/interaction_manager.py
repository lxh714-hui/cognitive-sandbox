from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from cognitive_sandbox.domain.actions import ActionCandidate
from cognitive_sandbox.domain.agent_context import AgentContext
from cognitive_sandbox.domain.interaction import AgentInteraction


class InteractionManager:
    """Resolve targeted candidate actions into interaction records."""

    def __init__(self, interaction_resolver: Any) -> None:
        if not callable(getattr(interaction_resolver, "resolve", None)):
            raise TypeError("interaction_resolver must provide a callable resolve method.")
        self._interaction_resolver = interaction_resolver

    def generate(
        self,
        agent_contexts: Iterable[AgentContext],
        actions: Iterable[ActionCandidate],
    ) -> tuple[AgentInteraction, ...]:
        if isinstance(agent_contexts, (str, bytes)):
            raise TypeError("agent_contexts must contain AgentContext values.")
        contexts = tuple(agent_contexts)
        if any(not isinstance(context, AgentContext) for context in contexts):
            raise TypeError("agent_contexts must contain only AgentContext values.")
        if isinstance(actions, (str, bytes)):
            raise TypeError("actions must contain ActionCandidate values.")
        candidates = tuple(actions)
        if any(not isinstance(action, ActionCandidate) for action in candidates):
            raise TypeError("actions must contain only ActionCandidate values.")

        agents_by_id = {context.character_id: context for context in contexts}
        interactions: list[AgentInteraction] = []
        for action in candidates:
            target_id = action.metadata.get("target_agent_id")
            if not isinstance(target_id, str) or not target_id.strip():
                continue
            source = agents_by_id.get(action.actor_id)
            target = agents_by_id.get(target_id)
            if source is None or target is None:
                continue
            interaction = self._interaction_resolver.resolve(source, target, action)
            if interaction is not None:
                interactions.append(interaction)
        return tuple(interactions)
