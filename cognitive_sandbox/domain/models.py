from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


@dataclass(frozen=True)
class World:
    id: str
    name: str
    description: str
    facts: tuple[str, ...] = ()


@dataclass(frozen=True)
class Agent:
    id: str
    world_id: str
    name: str
    role: str
    persona: str
    sprite_key: str


@dataclass(frozen=True)
class CognitiveMemory:
    id: str
    agent_id: str
    note: str
    source_event_id: str | None = None


@dataclass(frozen=True)
class ConversationEvent:
    id: str
    world_id: str
    agent_id: str
    kind: str
    content: str
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(cls, world_id: str, agent_id: str, kind: str, content: str) -> "ConversationEvent":
        return cls(id=str(uuid4()), world_id=world_id, agent_id=agent_id, kind=kind, content=content)
