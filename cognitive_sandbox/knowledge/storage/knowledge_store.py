from __future__ import annotations

from threading import RLock

from cognitive_sandbox.knowledge.models.knowledge_record import KnowledgeRecord
from cognitive_sandbox.knowledge.models.world_fact import WorldFact


class KnowledgeStore:
    """Small in-memory store with the same boundary expected from future persistence."""

    def __init__(self) -> None:
        self._facts: dict[str, WorldFact] = {}
        self._records: list[KnowledgeRecord] = []
        self._lock = RLock()

    def add_fact(self, fact: WorldFact) -> None:
        if not isinstance(fact, WorldFact):
            raise TypeError("fact must be a WorldFact.")
        with self._lock:
            if fact.id in self._facts:
                raise ValueError(f"world fact already exists: {fact.id}")
            self._facts[fact.id] = fact

    def add_knowledge(self, record: KnowledgeRecord) -> None:
        if not isinstance(record, KnowledgeRecord):
            raise TypeError("record must be a KnowledgeRecord.")
        with self._lock:
            if record.fact_id not in self._facts:
                raise KeyError(f"unknown world fact: {record.fact_id}")
            self._records.append(record)

    def query(self, character_id: str, query: str | None = None):
        """Return only records visible to this character, paired with their source facts."""
        if not isinstance(character_id, str) or not character_id.strip():
            raise ValueError("character_id must not be empty.")
        if query is not None and not isinstance(query, str):
            raise TypeError("query must be a string or None.")
        with self._lock:
            result = []
            for record in self._records:
                if not record.visibility.allows(character_id, record.owner_id):
                    continue
                if query and query.casefold() not in record.known_content.casefold():
                    continue
                fact = self._facts.get(record.fact_id)
                if fact is not None:
                    result.append((record, fact))
            return tuple(result)

    def get_fact(self, fact_id: str) -> WorldFact | None:
        """Administrative access for propagation/application services only."""
        with self._lock:
            return self._facts.get(fact_id)

    def facts_for_testing(self) -> tuple[WorldFact, ...]:
        """Return an immutable snapshot; normal character retrieval must use query()."""
        with self._lock:
            return tuple(self._facts.values())

    def snapshot(self) -> tuple[tuple[WorldFact, ...], tuple[KnowledgeRecord, ...]]:
        """Return immutable persistence data without exposing mutable store internals."""
        with self._lock:
            return tuple(self._facts.values()), tuple(self._records)
