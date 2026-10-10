from dataclasses import dataclass, field

import pytest

from cognitive_sandbox.application.service import SandboxService
from cognitive_sandbox.domain.models import Agent, ConversationEvent, World


@dataclass
class MemoryStore:
    events: list[ConversationEvent] = field(default_factory=list)

    def append(self, event: ConversationEvent) -> None:
        self.events.append(event)

    def list_for_world(self, world_id: str) -> list[ConversationEvent]:
        return [event for event in self.events if event.world_id == world_id]


class FixedProvider:
    label = "test provider"

    def __init__(self, reply: str = "Hello back") -> None:
        self.reply = reply

    def generate(self, world, agent, history, prompt) -> str:
        assert history[-1].kind == "player"
        assert history[-1].content == prompt
        return self.reply


def setup():
    return World("w", "World", "A place"), Agent("a", "w", "Agent", "guide", "kind", "a")


def test_submit_turn_persists_player_and_agent_events_in_order():
    world, agent = setup()
    store = MemoryStore()
    result = SandboxService(store, FixedProvider()).submit_turn(world, agent, "  Hi  ")

    assert [event.kind for event in store.events] == ["player", "agent"]
    assert [event.content for event in store.events] == ["Hi", "Hello back"]
    assert result.provider_label == "test provider"


def test_submit_turn_rejects_blank_input_without_saving():
    world, agent = setup()
    store = MemoryStore()

    with pytest.raises(ValueError, match="empty"):
        SandboxService(store, FixedProvider()).submit_turn(world, agent, "  ")

    assert store.events == []


def test_empty_provider_response_uses_fallback():
    world, agent = setup()
    store = MemoryStore()
    result = SandboxService(store, FixedProvider(" ")).submit_turn(world, agent, "Hi")

    assert result.reply_event.content
