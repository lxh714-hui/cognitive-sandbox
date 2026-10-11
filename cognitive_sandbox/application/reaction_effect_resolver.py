from __future__ import annotations

from cognitive_sandbox.domain.interaction_reaction import InteractionReaction
from cognitive_sandbox.domain.reaction_effect import ReactionEffect


class ReactionEffectResolver:
    """Translate a supported interaction reaction into unapplied effect data."""

    _EFFECTS = {
        "grateful": ("曾经有人帮助过我", 0.1, 0.05, -0.05),
        "protected": ("曾经有人保护过我", 0.05, 0.03, -0.02),
    }

    def resolve(self, reaction: InteractionReaction) -> ReactionEffect | None:
        if not isinstance(reaction, InteractionReaction):
            raise TypeError("reaction must be an InteractionReaction.")
        values = self._EFFECTS.get(reaction.reaction_type)
        if values is None:
            return None
        memory_content, relationship_delta, confidence_delta, stress_delta = values
        return ReactionEffect(
            reaction_id=reaction.interaction_id,
            target_agent_id=reaction.agent_id,
            memory_content=memory_content,
            relationship_delta=relationship_delta,
            confidence_delta=confidence_delta,
            stress_delta=stress_delta,
        )
