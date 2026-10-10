from __future__ import annotations

from dataclasses import dataclass

from cognitive_sandbox.application.ports import EventStore, TextGenerationProvider
from cognitive_sandbox.domain.models import Agent, ConversationEvent, World


@dataclass(frozen=True)
class TurnResult:
    player_event: ConversationEvent
    reply_event: ConversationEvent
    provider_label: str


class SandboxService:
    def __init__(self, store: EventStore, provider: TextGenerationProvider) -> None:
        self.store = store
        self.provider = provider

    def history(self, world: World) -> list[ConversationEvent]:
        return self.store.list_for_world(world.id)

    def submit_turn(self, world: World, agent: Agent, prompt: str) -> TurnResult:
        prompt = prompt.strip()
        if not prompt:
            raise ValueError("Message cannot be empty.")
        player_event = ConversationEvent.create(world.id, agent.id, "player", prompt)
        self.store.append(player_event)
        reply = self.generate_reply(world, agent, prompt)
        reply_event = self.record_agent_reply(world, agent, reply)
        return TurnResult(player_event, reply_event, self.provider.label)

    def generate_reply(self, world: World, agent: Agent, prompt: str) -> str:
        """Generate a reply after the player event has already been recorded."""
        history = self.store.list_for_world(world.id)
        reply = self.provider.generate(world, agent, history, prompt).strip()
        if not reply:
            reply = "我想了一下……你愿意再和我说说吗？"
        return reply

    def record_agent_reply(self, world: World, agent: Agent, content: str) -> ConversationEvent:
        event = ConversationEvent.create(world.id, agent.id, "agent", content)
        self.store.append(event)
        return event
