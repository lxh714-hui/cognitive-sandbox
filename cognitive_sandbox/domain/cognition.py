from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Any, Iterable, Mapping


class ProposalOperation(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    ACTIVATE = "activate"


def _source_refs(refs: Iterable[str]) -> tuple[str, ...]:
    if isinstance(refs, str):
        raise TypeError("source_refs must be a collection of source IDs, not one string.")
    normalized = tuple(refs)
    if not normalized:
        raise ValueError("source_refs must contain at least one source ID.")
    if any(not isinstance(ref, str) or not ref.strip() for ref in normalized):
        raise ValueError("source_refs must contain non-empty string IDs.")
    return normalized


def _validate_revision(name: str, value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer.")
    if value < 0:
        raise ValueError(f"{name} must be non-negative.")


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise TypeError("Working memory content keys must be strings.")
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, set):
        return frozenset(_freeze(item) for item in value)
    return value


def _validate_unit_interval(name: str, value: int | float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a number in its supported range.")
    if not 0 <= value <= 1:
        raise ValueError(f"{name} must be between 0 and 1.")
    return float(value)


@dataclass(frozen=True)
class CognitiveUpdateProposal:
    """A sourced request to change one agent's cognitive state."""

    proposal_id: str
    agent_id: str
    target_layer: str
    operation: ProposalOperation
    source_refs: tuple[str, ...]
    reason: str
    base_cognitive_revision: int
    world_revision: int

    def __post_init__(self) -> None:
        for field_name in ("proposal_id", "agent_id", "target_layer", "reason"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must not be empty.")
        if not isinstance(self.operation, ProposalOperation):
            try:
                object.__setattr__(self, "operation", ProposalOperation(self.operation))
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Unsupported proposal operation: {self.operation!r}.") from exc
        object.__setattr__(self, "source_refs", _source_refs(self.source_refs))
        _validate_revision("base_cognitive_revision", self.base_cognitive_revision)
        _validate_revision("world_revision", self.world_revision)


@dataclass(frozen=True)
class WorkingMemoryItem:
    item_id: str
    agent_id: str
    content: Mapping[str, Any]
    source_refs: tuple[str, ...]
    priority: float
    created_at: str

    def __post_init__(self) -> None:
        for name in ("item_id", "agent_id", "created_at"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must not be empty.")
        if not isinstance(self.content, Mapping):
            raise TypeError("content must be a mapping.")
        object.__setattr__(self, "content", _freeze(self.content))
        object.__setattr__(self, "source_refs", _source_refs(self.source_refs))
        object.__setattr__(self, "priority", _validate_unit_interval("priority", self.priority))


@dataclass(frozen=True)
class EmotionState:
    """Minimal valence/arousal state, scoped to one agent."""

    valence: float = 0.0
    arousal: float = 0.0
    source_refs: tuple[str, ...] = ()
    updated_at: str = ""

    def __post_init__(self) -> None:
        valence = self.valence
        if isinstance(valence, bool) or not isinstance(valence, (int, float)):
            raise TypeError("valence must be a number between -1 and 1.")
        if not -1 <= valence <= 1:
            raise ValueError("valence must be between -1 and 1.")
        object.__setattr__(self, "valence", float(valence))
        object.__setattr__(self, "arousal", _validate_unit_interval("arousal", self.arousal))
        if self.source_refs:
            object.__setattr__(self, "source_refs", _source_refs(self.source_refs))
        if not isinstance(self.updated_at, str):
            raise TypeError("updated_at must be a string.")


@dataclass(frozen=True)
class Belief:
    belief_id: str
    agent_id: str
    belief_type: str
    proposition: str
    confidence: float
    source_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in ("belief_id", "agent_id", "belief_type", "proposition"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must not be empty.")
        object.__setattr__(self, "confidence", _validate_unit_interval("confidence", self.confidence))
        object.__setattr__(self, "source_refs", _source_refs(self.source_refs))


@dataclass(frozen=True)
class AgentCognitiveState:
    agent_id: str
    cognitive_revision: int = 0
    working_memory: tuple[WorkingMemoryItem, ...] = ()
    emotion_state: EmotionState = EmotionState()
    beliefs: tuple[Belief, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.agent_id, str) or not self.agent_id.strip():
            raise ValueError("agent_id must not be empty.")
        _validate_revision("cognitive_revision", self.cognitive_revision)
        items = tuple(self.working_memory)
        if any(item.agent_id != self.agent_id for item in items):
            raise ValueError("Working memory items must belong to the state agent.")
        object.__setattr__(self, "working_memory", items)
        beliefs = tuple(self.beliefs)
        if any(belief.agent_id != self.agent_id for belief in beliefs):
            raise ValueError("Beliefs must belong to the state agent.")
        object.__setattr__(self, "beliefs", beliefs)


@dataclass(frozen=True)
class LongTermMemory:
    memory_id: str
    agent_id: str
    memory_type: str
    content: Mapping[str, Any]
    source_refs: tuple[str, ...]
    salience: float
    created_at: str

    def __post_init__(self) -> None:
        for name in ("memory_id", "agent_id", "memory_type", "created_at"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must not be empty.")
        if not isinstance(self.content, Mapping):
            raise TypeError("content must be a mapping.")
        object.__setattr__(self, "content", _freeze(self.content))
        object.__setattr__(self, "source_refs", _source_refs(self.source_refs))
        object.__setattr__(self, "salience", _validate_unit_interval("salience", self.salience))


@dataclass(frozen=True)
class Goal:
    goal_id: str
    agent_id: str
    goal_type: str
    description: str
    priority: float
    status: str
    source_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in ("goal_id", "agent_id", "goal_type", "description", "status"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must not be empty.")
        object.__setattr__(self, "priority", _validate_unit_interval("priority", self.priority))
        object.__setattr__(self, "source_refs", _source_refs(self.source_refs))


@dataclass(frozen=True)
class Relationship:
    relationship_id: str
    from_agent_id: str
    to_agent_id: str
    trust: float
    affinity: float
    hostility: float
    source_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in ("relationship_id", "from_agent_id", "to_agent_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must not be empty.")
        for name in ("trust", "affinity", "hostility"):
            object.__setattr__(self, name, _validate_unit_interval(name, getattr(self, name)))
        object.__setattr__(self, "source_refs", _source_refs(self.source_refs))
