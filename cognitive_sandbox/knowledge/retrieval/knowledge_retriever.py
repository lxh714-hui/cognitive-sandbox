from __future__ import annotations

from collections.abc import Mapping

from cognitive_sandbox.knowledge.models.knowledge_record import KnowledgeRecord
from cognitive_sandbox.knowledge.retrieval.knowledge_query import KnowledgeQuery
from cognitive_sandbox.knowledge.retrieval.retrieval_ranker import RetrievalRanker


class KnowledgeRetriever:
    def __init__(self, store, ranker: RetrievalRanker | None = None) -> None:
        if not callable(getattr(store, "query", None)):
            raise TypeError("store must provide query().")
        self._store = store
        self._ranker = ranker or RetrievalRanker()

    @property
    def backing_store(self):
        return self._store

    def snapshot(self):
        """Expose a read-only backing-store snapshot for persistence when supported."""
        snapshot = getattr(self._store, "snapshot", None)
        return snapshot() if callable(snapshot) else ((), ())

    def retrieve(self, character_id: str, query: KnowledgeQuery | str, current_context=None) -> tuple[KnowledgeRecord, ...]:
        if not isinstance(character_id, str) or not character_id.strip():
            raise ValueError("character_id must not be empty.")
        if isinstance(query, str):
            query = KnowledgeQuery(text=query)
        if not isinstance(query, KnowledgeQuery):
            raise TypeError("query must be KnowledgeQuery or str.")
        # Context is intentionally used only as query signal; it is never returned.
        context = current_context if isinstance(current_context, Mapping) else {}
        enriched = KnowledgeQuery(
            text=" ".join(part for part in (query.text, _context_text(context)) if part),
            tags=query.tags,
            related_entities=query.related_entities,
            limit=query.limit,
        )
        candidates = self._store.query(character_id)
        ranked = []
        for record, fact in candidates:
            ranked.append((self._ranker.score(record, fact, enriched), fact.timestamp, record))
        ranked.sort(key=lambda item: (item[0], item[1], item[2].confidence), reverse=True)
        return tuple(item[2] for item in ranked[:query.limit])


def _context_text(context: Mapping) -> str:
    safe_keys = {"location", "time", "visible_characters", "visible_objects", "visible_events", "environment_description"}
    values = []
    for key in safe_keys:
        value = context.get(key)
        if isinstance(value, str):
            values.append(value)
        elif isinstance(value, (tuple, list)):
            values.extend(item for item in value if isinstance(item, str))
    return " ".join(values)
