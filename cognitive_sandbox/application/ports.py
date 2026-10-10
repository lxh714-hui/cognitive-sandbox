from __future__ import annotations

from typing import Protocol

from cognitive_sandbox.domain.models import Agent, CognitiveMemory, ConversationEvent, World


class EventStore(Protocol):
    def append(self, event: ConversationEvent) -> None: ...
    def list_for_world(self, world_id: str) -> list[ConversationEvent]: ...


class TextGenerationProvider(Protocol):
    @property
    def label(self) -> str: ...
    def generate(self, world: World, agent: Agent, history: list[ConversationEvent], prompt: str) -> str: ...


class SpriteRenderer(Protocol):
    def render(self, sprite_key: str, expression: str = "neutral") -> object: ...


class MemoryProvider(Protocol):
    def list_for_agent(self, agent_id: str) -> list[CognitiveMemory]: ...
