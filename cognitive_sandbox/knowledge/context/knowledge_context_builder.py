from __future__ import annotations

from collections.abc import Iterable, Mapping
from types import MappingProxyType

from cognitive_sandbox.knowledge.retrieval.knowledge_query import KnowledgeQuery
from cognitive_sandbox.knowledge.retrieval.knowledge_retriever import KnowledgeRetriever


_SAFE_CONTEXT_KEYS = frozenset({
    "location", "time", "visible_characters", "visible_objects", "visible_events",
    "environment_description", "weather",
})


class KnowledgeContextBuilder:
    """Build an AI-safe context from scoped knowledge and explicitly visible scene data."""

    def __init__(self, retriever: KnowledgeRetriever) -> None:
        if not isinstance(retriever, KnowledgeRetriever):
            raise TypeError("retriever must be a KnowledgeRetriever.")
        self._retriever = retriever

    def build(
        self,
        character_id: str,
        query: KnowledgeQuery | str = "",
        *,
        current_context: Mapping | None = None,
        related_memories: Iterable[str] = (),
        available_information: Iterable[str] = (),
    ) -> Mapping:
        if current_context is not None and not isinstance(current_context, Mapping):
            raise TypeError("current_context must be a mapping or None.")
        memories = _texts(related_memories, "related_memories")
        available = _texts(available_information, "available_information")
        visible = _safe_scene(current_context or {})
        records = self._retriever.retrieve(character_id, query, current_context=visible)
        known = tuple(MappingProxyType({
            "fact_id": record.fact_id,
            "content": record.known_content,
            "knowledge_type": record.knowledge_type.value,
            "source": record.source.description,
            "confidence": record.confidence,
            "created_at": record.created_at,
        }) for record in records)
        return MappingProxyType({
            "character_id": character_id,
            "known_facts": known,
            "related_memories": memories,
            "current_context": visible,
            "available_information": available,
        })


def _safe_scene(context: Mapping) -> Mapping:
    # Unknown fields are discarded. In particular, WorldState metrics and hidden facts
    # are never forwarded wholesale to an AI context.
    return MappingProxyType({
        key: _sanitize_scene_value(key, value)
        for key, value in context.items()
        if key in _SAFE_CONTEXT_KEYS and _safe_value(value)
    })


def _safe_value(value) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (tuple, list)):
        return all(isinstance(item, (str, Mapping)) for item in value)
    if isinstance(value, Mapping):
        return all(isinstance(key, str) for key in value)
    return False


def _sanitize_scene_value(key: str, value):
    if key in {"visible_characters", "visible_objects", "visible_events"}:
        if isinstance(value, (tuple, list)):
            return tuple(_sanitize_visible_item(key, item) for item in value if _safe_value(item))
        return _sanitize_visible_item(key, value)
    return value.strip()


def _sanitize_visible_item(key: str, value):
    if isinstance(value, Mapping):
        allowed = {
            "visible_characters": {"name", "role", "description"},
            "visible_objects": {"name", "description", "type"},
            "visible_events": {"name", "description", "type"},
        }[key]
        return MappingProxyType({
            field: item.strip()
            for field, item in value.items()
            if field in allowed and isinstance(item, str) and item.strip()
        })
    return value.strip() if isinstance(value, str) else value


def _texts(values: Iterable[str], name: str) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        raise TypeError(f"{name} must be a collection of strings.")
    result = tuple(values)
    if any(not isinstance(value, str) or not value.strip() for value in result):
        raise ValueError(f"{name} must contain non-empty strings.")
    return result
