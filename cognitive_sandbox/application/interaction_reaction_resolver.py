from __future__ import annotations

from cognitive_sandbox.domain.agent_context import AgentContext
from cognitive_sandbox.domain.interaction import AgentInteraction
from cognitive_sandbox.domain.interaction_reaction import InteractionReaction


class InteractionReactionResolver:
    """Create a target-side reaction record for supported interactions."""

    _REACTIONS = {
        "help_other": ("grateful", "角色感受到帮助并产生感谢"),
        "protect_other": ("protected", "角色感受到保护"),
    }

    def resolve(
        self,
        interaction: AgentInteraction,
        target_agent: AgentContext,
    ) -> InteractionReaction | None:
        if not isinstance(interaction, AgentInteraction):
            raise TypeError("interaction must be an AgentInteraction.")
        if not isinstance(target_agent, AgentContext):
            raise TypeError("target_agent must be an AgentContext.")
        if target_agent.character_id != interaction.target_agent_id:
            raise ValueError("target_agent must match interaction.target_agent_id.")

        reaction = self._REACTIONS.get(interaction.interaction_type)
        if reaction is None:
            return None
        reaction_type, description = reaction
        return InteractionReaction(
            interaction_id=interaction.interaction_id,
            agent_id=target_agent.character_id,
            reaction_type=reaction_type,
            description=description,
        )
