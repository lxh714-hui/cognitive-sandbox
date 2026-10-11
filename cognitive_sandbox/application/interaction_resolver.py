from __future__ import annotations

from collections.abc import Callable
from uuid import uuid4

from cognitive_sandbox.domain.actions import ActionCandidate
from cognitive_sandbox.domain.agent_context import AgentContext
from cognitive_sandbox.domain.interaction import AgentInteraction


class InteractionResolver:
    """Create a minimal interaction record from a supported targeted action."""

    _INTERACTIONS = {
        "help": ("help_other", "角色尝试帮助另一个角色"),
        "protect": ("protect_other", "角色尝试保护另一个角色"),
    }

    def __init__(self, *, interaction_id_factory: Callable[[], str] | None = None) -> None:
        self._interaction_id_factory = interaction_id_factory or (lambda: f"interaction_{uuid4().hex}")

    def resolve(
        self,
        source_agent: AgentContext,
        target_agent: AgentContext | None,
        action: ActionCandidate,
    ) -> AgentInteraction | None:
        if not isinstance(source_agent, AgentContext):
            raise TypeError("source_agent must be an AgentContext.")
        if target_agent is not None and not isinstance(target_agent, AgentContext):
            raise TypeError("target_agent must be an AgentContext or None.")
        if not isinstance(action, ActionCandidate):
            raise TypeError("action must be an ActionCandidate.")
        if action.actor_id != source_agent.character_id:
            raise ValueError("action actor_id must match source_agent.character_id.")
        if target_agent is None or target_agent.character_id == source_agent.character_id:
            return None

        if action.target is not None and action.target != target_agent.character_id:
            return None
        if action.target_refs and target_agent.character_id not in action.target_refs:
            return None

        interaction = self._INTERACTIONS.get(action.intent.casefold())
        if interaction is None:
            return None
        interaction_id = self._interaction_id_factory()
        if not isinstance(interaction_id, str) or not interaction_id.strip():
            raise ValueError("interaction_id_factory must return a non-empty string.")
        interaction_type, description = interaction
        return AgentInteraction(
            interaction_id=interaction_id,
            source_agent_id=source_agent.character_id,
            target_agent_id=target_agent.character_id,
            interaction_type=interaction_type,
            description=description,
        )
