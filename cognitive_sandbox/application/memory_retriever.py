from __future__ import annotations

import re
import unicodedata
from typing import Protocol

from cognitive_sandbox.domain.cognition import LongTermMemory


class AgentMemoryStore(Protocol):
    def list_long_term_memories(self, agent_id: str) -> list[LongTermMemory]: ...


class MemoryRetriever:
    """Rank one agent's memories using deterministic lexical overlap."""

    _TOKEN_PATTERN = re.compile(r"[a-z0-9]+|[\u3400-\u9fff]+", re.IGNORECASE)

    def __init__(self, memory_store: AgentMemoryStore, *, max_results: int = 5) -> None:
        if isinstance(max_results, bool) or not isinstance(max_results, int):
            raise TypeError("max_results must be an integer.")
        if max_results < 1:
            raise ValueError("max_results must be positive.")
        self._memory_store = memory_store
        self._max_results = max_results

    def retrieve(self, agent_id: str, query: dict) -> list[LongTermMemory]:
        """Return the best matching memories owned by ``agent_id`` only."""
        if not isinstance(agent_id, str) or not agent_id.strip():
            raise ValueError("agent_id must not be empty.")
        if not isinstance(query, dict):
            raise TypeError("query must be a dictionary of focus terms.")
        query_values = list(self._strings(query))
        query_terms = self._tokens(query_values)
        if not query_terms:
            return []

        ranked: list[tuple[float, LongTermMemory]] = []
        # The storage call itself is agent-scoped; the owner check is an additional
        # boundary in case a different store implementation returns mixed records.
        for memory in self._memory_store.list_long_term_memories(agent_id):
            if memory.agent_id != agent_id:
                continue
            searchable_text = " ".join(self._strings(memory.content))
            normalized_text = self._normalize(searchable_text)
            memory_tokens = set(self._tokens((searchable_text,)))
            matched = 0
            for term in query_terms:
                if term in memory_tokens or (self._contains_cjk(term) and term in normalized_text):
                    matched += 1
            if matched:
                ranked.append((matched / len(query_terms), memory))

        ranked.sort(
            key=lambda result: (
                -result[0],
                -result[1].salience,
                result[1].created_at,
                result[1].memory_id,
            )
        )
        return [memory for _, memory in ranked[: self._max_results]]

    @classmethod
    def _strings(cls, value):
        if isinstance(value, str):
            if value.strip():
                yield cls._normalize(value)
        elif isinstance(value, dict) or hasattr(value, "values"):
            for nested in value.values():
                yield from cls._strings(nested)
        elif isinstance(value, (list, tuple, set, frozenset)):
            for nested in value:
                yield from cls._strings(nested)

    @classmethod
    def _tokens(cls, values) -> list[str]:
        tokens: list[str] = []
        for value in values:
            tokens.extend(cls._TOKEN_PATTERN.findall(cls._normalize(value)))
        return tokens

    @staticmethod
    def _normalize(value: str) -> str:
        return unicodedata.normalize("NFKC", value).casefold()

    @staticmethod
    def _contains_cjk(value: str) -> bool:
        return any("\u3400" <= char <= "\u9fff" for char in value)
