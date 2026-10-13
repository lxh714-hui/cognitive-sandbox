from __future__ import annotations

from dataclasses import dataclass

from cognitive_sandbox.knowledge.models.knowledge_record import KnowledgeType


@dataclass(frozen=True)
class PropagationRule:
    """A controlled disclosure rule for one explicitly supplied audience."""

    audience: str
    knowledge_type: KnowledgeType | str
    confidence: float
    source_type: str
    source_description: str
    known_content_template: str

    def __post_init__(self) -> None:
        for name in ("audience", "source_type", "source_description", "known_content_template"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must not be empty.")
        if self.audience not in {"participants", "observers", "reported_to", "rumor_recipients", "inferred_by"}:
            raise ValueError("unsupported propagation audience.")
        object.__setattr__(self, "knowledge_type", KnowledgeType(self.knowledge_type))
        if isinstance(self.confidence, bool) or not isinstance(self.confidence, (int, float)):
            raise TypeError("confidence must be between 0 and 1.")
        if not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be between 0 and 1.")
        object.__setattr__(self, "confidence", float(self.confidence))
