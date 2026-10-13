from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math

from cognitive_sandbox.knowledge.models.knowledge_source import KnowledgeSource
from cognitive_sandbox.knowledge.models.knowledge_visibility import KnowledgeVisibility


class KnowledgeType(str, Enum):
    DIRECT = "DIRECT"
    OBSERVED = "OBSERVED"
    REPORTED = "REPORTED"
    RUMOR = "RUMOR"
    INFERRED = "INFERRED"


@dataclass(frozen=True)
class KnowledgeRecord:
    """A character-scoped representation of a fact, with its own provenance."""

    owner_id: str
    fact_id: str
    knowledge_type: KnowledgeType | str
    source: KnowledgeSource
    confidence: float
    created_at: str
    known_content: str = ""
    visibility: KnowledgeVisibility = KnowledgeVisibility()

    def __post_init__(self) -> None:
        for name in ("owner_id", "fact_id", "created_at"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must not be empty.")
        if not isinstance(self.known_content, str):
            raise TypeError("known_content must be a string.")
        try:
            kind = KnowledgeType(self.knowledge_type)
        except ValueError as error:
            raise ValueError("knowledge_type must be DIRECT, OBSERVED, REPORTED, RUMOR, or INFERRED.") from error
        object.__setattr__(self, "knowledge_type", kind)
        if not isinstance(self.source, KnowledgeSource):
            raise TypeError("source must be a KnowledgeSource.")
        if not isinstance(self.visibility, KnowledgeVisibility):
            raise TypeError("visibility must be a KnowledgeVisibility.")
        if isinstance(self.confidence, bool) or not isinstance(self.confidence, (int, float)):
            raise TypeError("confidence must be between 0 and 1.")
        if not math.isfinite(self.confidence) or not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be between 0 and 1.")
        object.__setattr__(self, "confidence", float(self.confidence))
