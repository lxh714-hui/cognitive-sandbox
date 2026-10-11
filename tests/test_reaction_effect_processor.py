from dataclasses import FrozenInstanceError

import pytest

from cognitive_sandbox.application.reaction_effect_processor import ReactionEffectProcessor
from cognitive_sandbox.domain.agent_context import AgentContext
from cognitive_sandbox.domain.agent_state import AgentDynamicState
from cognitive_sandbox.domain.character import CharacterState
from cognitive_sandbox.domain.memory import InitialMemory
from cognitive_sandbox.domain.reaction_effect import ReactionEffect
from cognitive_sandbox.domain.relationship import RelationshipState


def _context():
    character = CharacterState("agent-b", "乙", "普通居民", (), (), (), ())
    return AgentContext(
        "agent-b",
        character,
        (InitialMemory("memory-old", "旧记忆", 0.3),),
        (RelationshipState("agent-b", "agent-a", "care", 0.5),),
        {"place": {"items": ["cup"]}},
        AgentDynamicState("agent-b", 0.5, 0.4, 0.7),
    )


def _effect(**overrides):
    values = {
        "reaction_id": "reaction-1",
        "target_agent_id": "agent-b",
        "memory_content": "曾经有人帮助过我",
        "relationship_delta": 0.1,
        "confidence_delta": 0.05,
        "stress_delta": -0.05,
    }
    values.update(overrides)
    return ReactionEffect(**values)


def test_grateful_effect_adds_memory():
    result = ReactionEffectProcessor(memory_id_factory=lambda: "memory-new").process(_effect(), _context())

    assert result.memory_added == (InitialMemory("memory-new", "曾经有人帮助过我", 0.5),)
    assert result.agent_context.memories[-1] == result.memory_added[0]


def test_relationship_trust_is_updated_and_clamped():
    result = ReactionEffectProcessor().process(_effect(relationship_delta=0.8), _context())

    assert result.relationship_changed is True
    assert result.agent_context.relationships[0].trust == 1.0


def test_dynamic_state_updates_confidence_and_stress_but_preserves_motivation():
    result = ReactionEffectProcessor().process(_effect(), _context())

    dynamic = result.agent_context.dynamic_state
    assert dynamic.confidence == pytest.approx(0.55)
    assert dynamic.stress == pytest.approx(0.35)
    assert dynamic.motivation == 0.7
    assert result.dynamic_state_changed is True


def test_effect_updates_multiple_components_without_mutating_original_context():
    context = _context()
    result = ReactionEffectProcessor(memory_id_factory=lambda: "memory-new").process(_effect(), context)

    assert len(result.agent_context.memories) == len(context.memories) + 1
    assert result.agent_context.relationships[0].trust == pytest.approx(0.6)
    assert result.agent_context.dynamic_state.confidence == pytest.approx(0.55)
    assert context.memories == (context.memories[0],)
    assert context.relationships[0].trust == 0.5
    assert context.dynamic_state.confidence == 0.5
    assert context.dynamic_state.stress == 0.4


def test_effect_can_be_processed_without_memory_or_relationships():
    context = _context()
    no_relations = AgentContext(
        context.character_id,
        context.character_state,
        context.memories,
        (),
        context.world_state,
        context.dynamic_state,
    )
    result = ReactionEffectProcessor().process(
        _effect(memory_content="", relationship_delta=0),
        no_relations,
    )

    assert result.memory_added == ()
    assert result.relationship_changed is False
    assert result.dynamic_state_changed is True


def test_processor_requires_effect_target_to_match_context():
    with pytest.raises(ValueError, match="target_agent_id"):
        ReactionEffectProcessor().process(_effect(target_agent_id="agent-other"), _context())


def test_result_is_immutable_and_added_memories_are_a_tuple():
    result = ReactionEffectProcessor(memory_id_factory=lambda: "memory-new").process(_effect(), _context())

    assert isinstance(result.memory_added, tuple)
    with pytest.raises(FrozenInstanceError):
        result.relationship_changed = False
    with pytest.raises(FrozenInstanceError):
        result.memory_added[0].content = "changed"
