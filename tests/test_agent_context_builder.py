from dataclasses import FrozenInstanceError

import pytest

from cognitive_sandbox.application.agent_context_builder import AgentContextBuilder
from cognitive_sandbox.domain.agent_context import AgentContext
from cognitive_sandbox.domain.agent_state import AgentDynamicState
from cognitive_sandbox.domain.character import CharacterState
from cognitive_sandbox.domain.memory import InitialMemory
from cognitive_sandbox.domain.relationship import RelationshipState


def test_builder_assembles_character_memory_relationships_and_world():
    character = CharacterState("char-1", "林夏", "医生", ("谨慎",), ("帮助他人",), (), ())
    memories = (InitialMemory("mem-1", "曾经帮助过一名病人", 0.5),)
    relationships = (RelationshipState("char-1", "patient", "care", 0.6),)
    world = {"setting": "clinic", "objects": [{"id": "cup"}]}

    context = AgentContextBuilder().build(character, memories, relationships, world)

    assert isinstance(context, AgentContext)
    assert context.character_id == "char-1"
    assert context.character_state is character
    assert context.memories == memories
    assert context.relationships == relationships
    assert context.world_state["setting"] == "clinic"
    assert context.world_state["objects"][0]["id"] == "cup"


def test_world_state_is_deeply_read_only_and_detached_from_input():
    world = {"nested": {"items": ["cup"]}}
    character = CharacterState("char-1", "林夏", "医生", (), (), (), ())

    context = AgentContextBuilder().build(character, (), (), world)
    world["nested"]["items"].append("book")

    assert context.world_state["nested"]["items"] == ("cup",)
    with pytest.raises(TypeError):
        context.world_state["nested"]["items"] = ()
    with pytest.raises(TypeError):
        context.world_state["nested"]["new"] = "value"


def test_context_and_collection_fields_are_immutable():
    character = CharacterState("char-1", "林夏", "医生", (), (), (), ())
    context = AgentContextBuilder().build(character, [], [], {})

    assert context.memories == ()
    assert context.relationships == ()
    with pytest.raises(FrozenInstanceError):
        context.character_id = "other"
    with pytest.raises(AttributeError):
        context.memories.append(InitialMemory("mem", "past", 0.2))


def test_builder_accepts_empty_memories_and_relationships():
    character = CharacterState("char-1", "路人", "普通居民", (), (), (), ())

    context = AgentContextBuilder().build(character, (), (), {"setting": "town"})

    assert context.memories == ()
    assert context.relationships == ()


def test_context_rejects_character_id_that_does_not_match_state():
    character = CharacterState("char-1", "林夏", "医生", (), (), (), ())
    with pytest.raises(ValueError, match="must match"):
        AgentContext("different", character, (), (), {})


def test_builder_saves_provided_dynamic_state():
    character = CharacterState("char-1", "林夏", "医生", (), (), (), ())
    dynamic_state = AgentDynamicState("char-1", 0.8, 0.3, 0.7)

    context = AgentContextBuilder().build(
        character, (), (), {}, dynamic_state=dynamic_state
    )

    assert context.dynamic_state is dynamic_state


def test_builder_uses_default_dynamic_state_when_omitted():
    character = CharacterState("char-1", "林夏", "医生", (), (), (), ())

    context = AgentContextBuilder().build(character, (), (), {})

    assert context.dynamic_state == AgentDynamicState("char-1", 0.5, 0.0, 0.5)
