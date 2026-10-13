from __future__ import annotations

from collections.abc import Iterable, Mapping
from types import MappingProxyType
from typing import Any

from cognitive_sandbox.domain.character_mind import CharacterMind
from cognitive_sandbox.application.prompts.character_mind_prompt import build_character_mind_prompt
from cognitive_sandbox.knowledge.retrieval.knowledge_retriever import KnowledgeRetriever


_SAFE_SCENE_KEYS = frozenset({
    "location", "time", "visible_characters", "visible_objects", "visible_events",
    "environment_description", "weather", "situation", "current_event", "emotional_style",
})


class AIContextBuilder:
    """Create a prompt-safe view from a CharacterMind and explicitly visible data."""

    def __init__(self, knowledge_retriever: KnowledgeRetriever | None = None) -> None:
        if knowledge_retriever is not None and not callable(
            getattr(knowledge_retriever, "retrieve", None)
        ):
            raise TypeError("knowledge_retriever must provide retrieve().")
        self._knowledge_retriever = knowledge_retriever

    def build(
        self,
        mind: CharacterMind,
        *,
        current_scene: Mapping[str, Any],
        player_visible_information: Iterable[str] = (),
        character_id: str | None = None,
        knowledge_query: str = "",
        cognitive_context: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        if not isinstance(mind, CharacterMind):
            raise TypeError("mind must be a CharacterMind.")
        if not isinstance(current_scene, Mapping):
            raise TypeError("current_scene must be a mapping of scene information.")
        if isinstance(player_visible_information, (str, bytes)):
            raise TypeError("player_visible_information must be a collection of strings.")
        visible = tuple(player_visible_information)
        if any(not isinstance(item, str) or not item.strip() for item in visible):
            raise ValueError("player_visible_information must contain non-empty strings.")
        if any(not isinstance(key, str) for key in current_scene):
            raise TypeError("current_scene keys must be strings.")
        if character_id is not None and (
            not isinstance(character_id, str) or not character_id.strip()
        ):
            raise ValueError("character_id must be a non-empty string or None.")
        if not isinstance(knowledge_query, str):
            raise TypeError("knowledge_query must be a string.")

        safe_scene = _safe_scene(current_scene)
        knowledge = mind.knowledge_context
        records = knowledge.records
        if knowledge.owner_id is not None and character_id is not None:
            if knowledge.owner_id != character_id:
                raise ValueError("CharacterMind knowledge belongs to a different character.")
        if self._knowledge_retriever is not None and character_id is not None:
            retrieved = self._knowledge_retriever.retrieve(
                character_id, knowledge_query, current_context=safe_scene
            )
            by_record = {(record.owner_id, record.fact_id): record for record in records}
            by_record.update({(record.owner_id, record.fact_id): record for record in retrieved})
            records = tuple(by_record.values())
        known_facts = tuple(
            {
                "content": record.known_content,
                "knowledge_type": record.knowledge_type.value,
                "source": record.source.description,
                "confidence": record.confidence,
            }
            for record in records
            if record.known_content.strip()
        )

        identity = mind.identity
        profile = mind.personality
        style = mind.speech_style
        memory = mind.get_character_memory()
        relationship_context = mind.relationship_context
        if character_id is not None and relationship_context.owner_id not in (None, character_id):
            raise ValueError("CharacterMind relationship context belongs to a different character.")
        relationship_is_scoped = (
            relationship_context.owner_id is None
            or character_id is None
            or relationship_context.owner_id == character_id
        )
        payload = {
            "instructions": build_character_mind_prompt(),
            "identity": {
                "name": identity.name,
                "role": identity.role,
                "background": identity.background,
            },
            "personality": {
                "traits": profile.traits,
                "values": profile.values,
                "goals": profile.goals,
                "fears": profile.fears,
                "taboos": profile.taboos,
            },
            "speech_style": {
                "tone": style.tone,
                "vocabulary": style.vocabulary,
                "sentence_style": style.sentence_style,
                "preferred_phrases": style.preferred_phrases,
                "forbidden_styles": style.forbidden_styles,
            },
            "memory": {
                "stable": memory.stable_memory,
                "relationship": memory.relationship_memory,
                "recent": memory.recent_memory,
            },
            "relationship_context": {
                "relationships": tuple(
                    {
                        "target": "当前交谈对象",
                        "trust": relationship.trust,
                        "respect": relationship.respect,
                        "fear": relationship.fear,
                        "affinity": relationship.affinity,
                        "hostility": relationship.hostility,
                    }
                    for relationship in relationship_context.relationships
                    if relationship_is_scoped
                ),
            },
            "example_dialogues": tuple(
                {"user": example.user, "character": example.character}
                for example in mind.example_dialogues
            ),
            "knowledge_context": {
                "known_facts": known_facts,
                "available_information": knowledge.available_information,
            },
            "current_scene": safe_scene,
            "player_visible_information": visible,
        }
        if cognitive_context is not None:
            if not isinstance(cognitive_context, Mapping):
                raise TypeError("cognitive_context must be a mapping.")
            # This is a role-local interpretation view, not world facts or global state.
            payload["cognitive_context"] = {
                key: cognitive_context[key]
                for key in ("cognitive_style", "reasoning_profile", "current_interpretation", "observation_focus")
                if key in cognitive_context
            }
        return _freeze_mapping(payload)

    def get_character_memory(self, mind: CharacterMind):
        if not isinstance(mind, CharacterMind):
            raise TypeError("mind must be a CharacterMind.")
        return mind.get_character_memory()


def _freeze_mapping(values: Mapping[str, Any]) -> Mapping[str, Any]:
    frozen: dict[str, Any] = {}
    for key, value in values.items():
        if isinstance(value, Mapping):
            if any(not isinstance(nested_key, str) for nested_key in value):
                raise TypeError("current_scene mapping keys must be strings.")
            frozen[key] = _freeze_mapping(value)
        elif isinstance(value, (tuple, list)):
            frozen[key] = tuple(_freeze_value(item) for item in value)
        elif isinstance(value, set):
            frozen[key] = frozenset(_freeze_value(item) for item in value)
        else:
            frozen[key] = value
    return MappingProxyType(frozen)


def _safe_scene(values: Mapping[str, Any]) -> Mapping[str, Any]:
    """Discard aggregate state and unknown fields; retain only player-visible scene data."""
    safe: dict[str, Any] = {}
    for key, value in values.items():
        if key not in _SAFE_SCENE_KEYS:
            continue
        if isinstance(value, str):
            if value.strip():
                safe[key] = value.strip()
        elif key in {"visible_characters", "visible_objects", "visible_events"} and isinstance(
            value, (tuple, list)
        ):
            allowed_fields = {
                "visible_characters": {"name", "role", "description"},
                "visible_objects": {"name", "description", "type"},
                "visible_events": {"name", "description", "type"},
            }[key]
            items = []
            for item in value:
                if isinstance(item, str) and item.strip():
                    items.append(item.strip())
                elif isinstance(item, Mapping):
                    items.append({
                        field: text.strip()
                        for field, text in item.items()
                        if field in allowed_fields and isinstance(text, str) and text.strip()
                    })
            safe[key] = tuple(items)
    return _freeze_mapping(safe)


def _freeze_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise TypeError("current_scene mapping keys must be strings.")
        return _freeze_mapping(value)
    if isinstance(value, (tuple, list)):
        return tuple(_freeze_value(item) for item in value)
    if isinstance(value, set):
        return frozenset(_freeze_value(item) for item in value)
    return value
