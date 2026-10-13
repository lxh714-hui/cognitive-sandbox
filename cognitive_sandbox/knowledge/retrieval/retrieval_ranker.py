from __future__ import annotations

from datetime import datetime
from cognitive_sandbox.knowledge.models.knowledge_record import KnowledgeRecord
from cognitive_sandbox.knowledge.models.world_fact import WorldFact
from cognitive_sandbox.knowledge.retrieval.knowledge_query import KnowledgeQuery


class RetrievalRanker:
    """Deterministic ranking using lexical overlap, entity links, importance, and recency."""

    def score(self, record: KnowledgeRecord, fact: WorldFact, query: KnowledgeQuery) -> float:
        text_tokens = _tokens(query.text)
        record_tokens = _tokens(record.known_content) | _tokens(fact.fact_type)
        tags = {tag.casefold() for tag in query.tags}
        entity_ids = {value.casefold() for value in query.related_entities}
        lexical = len(text_tokens & record_tokens) / max(len(text_tokens), 1)
        tag_match = 1.0 if tags & record_tokens else 0.0
        entity_match = 1.0 if entity_ids & {item.casefold() for item in fact.related_entities} else 0.0
        recency = _recency(record.created_at)
        return lexical * 0.4 + tag_match * 0.15 + entity_match * 0.2 + fact.importance * 0.2 + recency * 0.05


def _tokens(text: str) -> set[str]:
    # Keep CJK text as characters and Latin/numeric words as whole tokens.
    import re

    words = set(re.findall(r"[a-z0-9_]+", text.casefold()))
    cjk = re.findall(r"[\u3400-\u9fff]", text)
    words.update(cjk)
    words.update(text.casefold()[i:i + 2] for i in range(max(0, len(text) - 1)))
    return words


def _recency(timestamp: str) -> float:
    try:
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        return parsed.timestamp() / 4_102_444_800  # normalized through year 2100
    except (ValueError, OverflowError):
        return 0.5
