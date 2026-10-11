from dataclasses import FrozenInstanceError

import pytest

from cognitive_sandbox.application.memory_updater import MemoryUpdater
from cognitive_sandbox.domain.agent_context import AgentContext
from cognitive_sandbox.domain.character import CharacterState
from cognitive_sandbox.domain.memory import InitialMemory
from cognitive_sandbox.domain.relationship import RelationshipState
from cognitive_sandbox.domain.world_events import WorldEvent


def make_context(memories=()):
    character = CharacterState("agent-1", "林夏", "医生", (), (), (), ())
    relationship = RelationshipState("agent-1", "patient", "care", 0.6)
    return AgentContext("agent-1", character, memories, (relationship,), {"room": "clinic"})


def make_event(event_type):
    return WorldEvent("event-1", "main", "world-1", event_type, "agent-1", {}, 1)


@pytest.mark.parametrize(
    ("event_type", "content", "importance"),
    [
        ("help_attempt", "我曾经帮助过他人", 0.6),
        ("protect_attempt", "我曾经保护过目标", 0.7),
        ("observe_action", "我曾经观察并收集过信息", 0.3),
        ("action_failed", "我曾经经历过一次失败的行动", 0.5),
    ],
)
def test_known_event_creates_expected_memory(event_type, content, importance):
    updater = MemoryUpdater(memory_id_factory=lambda: "memory-new")

    memories = updater.update(make_context(), make_event(event_type))

    assert len(memories) == 1
    assert memories[0] == InitialMemory("memory-new", content, importance)


def test_unknown_event_returns_existing_memories_unchanged():
    existing = (InitialMemory("memory-old", "过去的经历", 0.4),)

    memories = MemoryUpdater().update(make_context(existing), make_event("unknown"))

    assert memories == existing


def test_update_preserves_existing_memories_and_does_not_mutate_context():
    existing = (InitialMemory("memory-old", "过去的经历", 0.4),)
    context = make_context(existing)
    updater = MemoryUpdater(memory_id_factory=lambda: "memory-new")

    updated = updater.update(context, make_event("help_attempt"))

    assert updated == (existing[0], InitialMemory("memory-new", "我曾经帮助过他人", 0.6))
    assert context.memories == existing
    assert context.relationships == (RelationshipState("agent-1", "patient", "care", 0.6),)
    assert context.world_state["room"] == "clinic"


def test_generated_memory_is_immutable_and_id_must_be_unique():
    context = make_context()
    memory = MemoryUpdater(memory_id_factory=lambda: "memory-new").update(
        context, make_event("protect_attempt")
    )[0]
    with pytest.raises(FrozenInstanceError):
        memory.content = "changed"

    duplicate_context = make_context((InitialMemory("duplicate", "已有记忆", 0.2),))
    with pytest.raises(ValueError, match="already used"):
        MemoryUpdater(memory_id_factory=lambda: "duplicate").update(
            duplicate_context, make_event("help_attempt")
        )
