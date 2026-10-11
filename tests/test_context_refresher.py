from dataclasses import FrozenInstanceError

import pytest

from cognitive_sandbox.application.context_refresher import ContextRefresher
from cognitive_sandbox.domain.agent_context import AgentContext
from cognitive_sandbox.domain.agent_state import AgentDynamicState
from cognitive_sandbox.domain.character import CharacterState
from cognitive_sandbox.domain.memory import InitialMemory
from cognitive_sandbox.domain.relationship import RelationshipState


def make_context():
    character = CharacterState("agent-1", "林夏", "医生", ("细心",), ("帮助他人",), (), ())
    memories = (InitialMemory("memory-1", "曾经帮助过一名病人", 0.5),)
    relationships = (RelationshipState("agent-1", "patient", "care", 0.6),)
    dynamic_state = AgentDynamicState("agent-1", 0.9, 0.4, 0.8)
    return AgentContext(
        "agent-1", character, memories, relationships, {"weather": "clear"}, dynamic_state
    )


def test_refresh_replaces_world_state_and_preserves_agent_data():
    existing = make_context()
    new_world_state = {"weather": "rain", "location": "clinic"}

    refreshed = ContextRefresher().refresh(existing, new_world_state)

    assert refreshed is not existing
    assert refreshed.world_state == new_world_state
    assert refreshed.character_state is existing.character_state
    assert refreshed.memories == existing.memories
    assert refreshed.relationships == existing.relationships
    assert refreshed.dynamic_state is existing.dynamic_state


def test_refresh_does_not_change_existing_context():
    existing = make_context()
    old_world_state = dict(existing.world_state)

    ContextRefresher().refresh(existing, {"weather": "rain"})

    assert dict(existing.world_state) == old_world_state


def test_refreshed_context_is_immutable_and_world_state_is_deeply_read_only():
    existing = make_context()
    refreshed = ContextRefresher().refresh(existing, {"nested": {"items": ["cup"]}})

    with pytest.raises(FrozenInstanceError):
        refreshed.character_id = "other"
    with pytest.raises(TypeError):
        refreshed.world_state["nested"]["items"][0] = "book"


def test_refresher_reuses_injected_builder():
    class RecordingBuilder:
        def __init__(self):
            self.calls = []

        def build(self, character_state, memories, relationships, world_state, *, dynamic_state=None):
            self.calls.append((character_state, memories, relationships, world_state, dynamic_state))
            return AgentContext(
                character_state.character_id,
                character_state,
                tuple(memories),
                tuple(relationships),
                world_state,
                dynamic_state,
            )

    existing = make_context()
    builder = RecordingBuilder()
    updated_state = {"weather": "windy"}

    result = ContextRefresher(builder).refresh(existing, updated_state)

    assert builder.calls == [
        (
            existing.character_state,
            existing.memories,
            existing.relationships,
            updated_state,
            existing.dynamic_state,
        )
    ]
    assert result.world_state["weather"] == "windy"


def test_refresh_rejects_invalid_inputs():
    refresher = ContextRefresher()
    with pytest.raises(TypeError, match="AgentContext"):
        refresher.refresh({}, {})
    with pytest.raises(TypeError, match="new_world_state"):
        refresher.refresh(make_context(), None)
