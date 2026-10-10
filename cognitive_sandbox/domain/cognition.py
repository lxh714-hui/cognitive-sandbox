from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable


class ProposalOperation(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    ACTIVATE = "activate"


def _source_refs(refs: Iterable[str]) -> tuple[str, ...]:
    if isinstance(refs, str):
        raise TypeError("source_refs must be a collection of source IDs, not one string.")
    normalized = tuple(refs)
    if not normalized:
        raise ValueError("source_refs must contain at least one source ID.")
    if any(not isinstance(ref, str) or not ref.strip() for ref in normalized):
        raise ValueError("source_refs must contain non-empty string IDs.")
    return normalized


def _validate_revision(name: str, value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer.")
    if value < 0:
        raise ValueError(f"{name} must be non-negative.")


@dataclass(frozen=True)
class CognitiveUpdateProposal:
    """A sourced request to change one agent's cognitive state."""

    proposal_id: str
    agent_id: str
    target_layer: str
    operation: ProposalOperation
    source_refs: tuple[str, ...]
    reason: str
    base_cognitive_revision: int
    world_revision: int

    def __post_init__(self) -> None:
        for field_name in ("proposal_id", "agent_id", "target_layer", "reason"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must not be empty.")
        if not isinstance(self.operation, ProposalOperation):
            try:
                object.__setattr__(self, "operation", ProposalOperation(self.operation))
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Unsupported proposal operation: {self.operation!r}.") from exc
        object.__setattr__(self, "source_refs", _source_refs(self.source_refs))
        _validate_revision("base_cognitive_revision", self.base_cognitive_revision)
        _validate_revision("world_revision", self.world_revision)
