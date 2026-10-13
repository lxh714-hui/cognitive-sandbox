from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from cognitive_sandbox.domain.character_card import ExampleDialogue
from cognitive_sandbox.relationship.relationship_state import RelationshipState as WorldRelationshipState
from cognitive_sandbox.knowledge.models.knowledge_record import KnowledgeRecord


def _texts(values: Iterable[str], field_name: str) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        raise TypeError(f"{field_name} must be a collection of strings.")
    try:
        result = tuple(values)
    except TypeError as error:
        raise TypeError(f"{field_name} must be a collection of strings.") from error
    if any(not isinstance(value, str) or not value.strip() for value in result):
        raise ValueError(f"{field_name} must contain non-empty strings.")
    return result


@dataclass(frozen=True)
class Identity:
    name: str
    role: str
    background: str = ""

    def __post_init__(self) -> None:
        for field_name in ("name", "role"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must not be empty.")
        if not isinstance(self.background, str):
            raise TypeError("background must be a string.")


@dataclass(frozen=True)
class PersonalityProfile:
    traits: tuple[str, ...] = ()
    values: tuple[str, ...] = ()
    goals: tuple[str, ...] = ()
    fears: tuple[str, ...] = ()
    taboos: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for field_name in ("traits", "values", "goals", "fears", "taboos"):
            object.__setattr__(self, field_name, _texts(getattr(self, field_name), field_name))


@dataclass(frozen=True)
class SpeechStyle:
    tone: str = "自然、克制"
    vocabulary: tuple[str, ...] = ()
    sentence_style: str = "清晰、简洁"
    preferred_phrases: tuple[str, ...] = ()
    forbidden_styles: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for field_name in ("tone", "sentence_style"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must not be empty.")
        for field_name in ("vocabulary", "preferred_phrases", "forbidden_styles"):
            object.__setattr__(self, field_name, _texts(getattr(self, field_name), field_name))


@dataclass(frozen=True)
class MemoryContext:
    """Read-only memory views supplied to a character; contains no write API."""

    stable_memory: tuple[str, ...] = ()
    relationship_memory: tuple[str, ...] = ()
    recent_memory: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for field_name in ("stable_memory", "relationship_memory", "recent_memory"):
            object.__setattr__(self, field_name, _texts(getattr(self, field_name), field_name))


@dataclass(frozen=True)
class KnowledgeContext:
    """Immutable knowledge snapshot scoped to owner_id; it has no write interface."""

    records: tuple[KnowledgeRecord, ...] = ()
    available_information: tuple[str, ...] = ()
    owner_id: str | None = None

    def __post_init__(self) -> None:
        records = tuple(self.records)
        if any(not isinstance(record, KnowledgeRecord) for record in records):
            raise TypeError("records must contain only KnowledgeRecord values.")
        owners = {record.owner_id for record in records}
        owner_id = self.owner_id
        if owner_id is None and len(owners) == 1:
            owner_id = next(iter(owners))
        if owner_id is None and len(owners) > 1:
            raise ValueError("owner_id is required for a mixed-source knowledge context.")
        if owner_id is not None and (not isinstance(owner_id, str) or not owner_id.strip()):
            raise ValueError("owner_id must be a non-empty string or None.")
        object.__setattr__(self, "records", records)
        object.__setattr__(self, "owner_id", owner_id)
        object.__setattr__(
            self,
            "available_information",
            _texts(self.available_information, "available_information"),
        )


@dataclass(frozen=True)
class RelationshipContext:
    """Read-only, owner-scoped directional relationships for one character."""

    owner_id: str | None = None
    relationships: tuple[WorldRelationshipState, ...] = ()

    def __post_init__(self):
        relationships = tuple(self.relationships)
        if any(not isinstance(item, WorldRelationshipState) for item in relationships):
            raise TypeError("relationships must contain world RelationshipState values.")
        owner_id = self.owner_id
        owners = {item.source_id for item in relationships}
        if owner_id is None and len(owners) == 1:
            owner_id = next(iter(owners))
        if len(owners) > 1 or (owner_id is not None and owners and owners != {owner_id}):
            raise ValueError("RelationshipContext may contain only relationships owned by owner_id.")
        if owner_id is not None and (not isinstance(owner_id, str) or not owner_id.strip()):
            raise ValueError("owner_id must be a non-empty string or None.")
        object.__setattr__(self, "owner_id", owner_id)
        object.__setattr__(self, "relationships", relationships)


@dataclass(frozen=True)
class CharacterMind:
    identity: Identity
    personality: PersonalityProfile
    speech_style: SpeechStyle = SpeechStyle()
    memory_context: MemoryContext = MemoryContext()
    example_dialogues: tuple[ExampleDialogue, ...] = ()
    knowledge_context: KnowledgeContext = KnowledgeContext()
    relationship_context: RelationshipContext = RelationshipContext()

    def __post_init__(self) -> None:
        if not isinstance(self.identity, Identity):
            raise TypeError("identity must be an Identity.")
        if not isinstance(self.personality, PersonalityProfile):
            raise TypeError("personality must be a PersonalityProfile.")
        if not isinstance(self.speech_style, SpeechStyle):
            raise TypeError("speech_style must be a SpeechStyle.")
        if not isinstance(self.memory_context, MemoryContext):
            raise TypeError("memory_context must be a MemoryContext.")
        if not isinstance(self.knowledge_context, KnowledgeContext):
            raise TypeError("knowledge_context must be a KnowledgeContext.")
        if not isinstance(self.relationship_context, RelationshipContext):
            raise TypeError("relationship_context must be a RelationshipContext.")
        examples = tuple(self.example_dialogues)
        if any(not isinstance(item, ExampleDialogue) for item in examples):
            raise TypeError("example_dialogues must contain only ExampleDialogue values.")
        object.__setattr__(self, "example_dialogues", examples)

    def get_character_memory(self) -> MemoryContext:
        """Return the immutable memory snapshot available for prompt construction."""
        return self.memory_context
