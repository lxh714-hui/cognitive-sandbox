from __future__ import annotations

from collections.abc import Iterable

from cognitive_sandbox.domain.character_card import CharacterCard
from cognitive_sandbox.domain.character_mind import (
    CharacterMind,
    Identity,
    KnowledgeContext,
    MemoryContext,
    PersonalityProfile,
    SpeechStyle,
)


class CharacterMindBuilder:
    """Build a read-only role context from content cards and supplied memories."""

    def build(
        self,
        card: CharacterCard,
        *,
        speech_style: SpeechStyle | None = None,
        values: Iterable[str] = (),
        fears: Iterable[str] = (),
        relationship_memory: Iterable[str] = (),
        recent_memory: Iterable[str] = (),
        knowledge_context: KnowledgeContext | None = None,
    ) -> CharacterMind:
        if not isinstance(card, CharacterCard):
            raise TypeError("card must be a CharacterCard.")
        values = _text_values(values, "values")
        fears = _text_values(fears, "fears")
        relationship_memory = _text_values(relationship_memory, "relationship_memory")
        recent_memory = _text_values(recent_memory, "recent_memory")
        stable_memory = (card.background,) if card.background.strip() else ()
        card_values = tuple(
            constraint.content
            for constraint in card.constraints
            if constraint.type in {"soft", "preference"}
        )
        taboos = tuple(
            constraint.content for constraint in card.constraints if constraint.type == "hard"
        )
        return CharacterMind(
            identity=Identity(card.name, card.occupation or "角色", card.background),
            personality=PersonalityProfile(
                traits=card.personality,
                values=(*card_values, *values),
                goals=card.goals,
                fears=fears,
                taboos=taboos,
            ),
            speech_style=speech_style or SpeechStyle(),
            memory_context=MemoryContext(
                stable_memory=stable_memory,
                relationship_memory=relationship_memory,
                recent_memory=recent_memory,
            ),
            example_dialogues=card.example_dialogues,
            knowledge_context=knowledge_context or KnowledgeContext(),
        )


def _text_values(values: Iterable[str], field_name: str) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        raise TypeError(f"{field_name} must be a collection of strings.")
    try:
        result = tuple(values)
    except TypeError as error:
        raise TypeError(f"{field_name} must be a collection of strings.") from error
    if any(not isinstance(value, str) or not value.strip() for value in result):
        raise ValueError(f"{field_name} must contain non-empty strings.")
    return result
