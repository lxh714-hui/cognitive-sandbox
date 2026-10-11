from __future__ import annotations

from collections.abc import Callable
from uuid import uuid4

from cognitive_sandbox.domain.agent_context import AgentContext
from cognitive_sandbox.domain.agent_state import AgentDynamicState
from cognitive_sandbox.domain.memory import InitialMemory
from cognitive_sandbox.domain.reaction_effect import ReactionEffect
from cognitive_sandbox.domain.reaction_effect_result import ReactionEffectResult
from cognitive_sandbox.domain.relationship import RelationshipState


class ReactionEffectProcessor:
    """Apply effect data to a detached AgentContext snapshot."""

    def __init__(self, *, memory_id_factory: Callable[[], str] | None = None) -> None:
        self._memory_id_factory = memory_id_factory or (lambda: f"memory_reaction_{uuid4().hex}")

    def process(
        self,
        reaction_effect: ReactionEffect,
        target_agent: AgentContext,
    ) -> ReactionEffectResult:
        if not isinstance(reaction_effect, ReactionEffect):
            raise TypeError("reaction_effect must be a ReactionEffect.")
        if not isinstance(target_agent, AgentContext):
            raise TypeError("target_agent must be an AgentContext.")
        if reaction_effect.target_agent_id != target_agent.character_id:
            raise ValueError("reaction_effect target_agent_id must match target_agent.character_id.")

        memory_added: tuple[InitialMemory, ...] = ()
        memories = target_agent.memories
        if reaction_effect.memory_content:
            memory_id = self._memory_id_factory()
            if not isinstance(memory_id, str) or not memory_id.strip():
                raise ValueError("memory_id_factory must return a non-empty string.")
            if memory_id in {memory.memory_id for memory in memories}:
                raise ValueError("memory_id_factory returned an ID already used by this agent.")
            memory_added = (InitialMemory(memory_id, reaction_effect.memory_content, 0.5),)
            memories = (*memories, *memory_added)

        relationship_changed = False
        relationships: list[RelationshipState] = []
        for relationship in target_agent.relationships:
            trust = min(1.0, max(0.0, relationship.trust + reaction_effect.relationship_delta))
            if trust != relationship.trust:
                relationship_changed = True
                relationships.append(
                    RelationshipState(
                        source_id=relationship.source_id,
                        target_id=relationship.target_id,
                        relation_type=relationship.relation_type,
                        trust=trust,
                    )
                )
            else:
                relationships.append(relationship)

        prior_dynamic = target_agent.dynamic_state
        confidence = min(1.0, max(0.0, prior_dynamic.confidence + reaction_effect.confidence_delta))
        stress = min(1.0, max(0.0, prior_dynamic.stress + reaction_effect.stress_delta))
        dynamic_state_changed = confidence != prior_dynamic.confidence or stress != prior_dynamic.stress
        dynamic_state = (
            AgentDynamicState(
                character_id=prior_dynamic.character_id,
                confidence=confidence,
                stress=stress,
                motivation=prior_dynamic.motivation,
            )
            if dynamic_state_changed
            else prior_dynamic
        )

        updated_context = AgentContext(
            character_id=target_agent.character_id,
            character_state=target_agent.character_state,
            memories=memories,
            relationships=tuple(relationships),
            world_state=target_agent.world_state,
            dynamic_state=dynamic_state,
        )
        return ReactionEffectResult(
            agent_context=updated_context,
            memory_added=memory_added,
            relationship_changed=relationship_changed,
            dynamic_state_changed=dynamic_state_changed,
        )
