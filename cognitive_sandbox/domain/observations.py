from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


def _source_refs(refs: Iterable[str]) -> tuple[str, ...]:
    if isinstance(refs, str):
        raise TypeError("source_refs must be a collection of source IDs, not one string.")
    normalized = tuple(refs)
    if not normalized:
        raise ValueError("source_refs must contain at least one source ID.")
    if any(not isinstance(ref, str) or not ref.strip() for ref in normalized):
        raise ValueError("source_refs must contain non-empty string IDs.")
    return normalized


@dataclass(frozen=True)
class ObservationRecord:
    """Information actually perceived by one agent, with its source IDs."""

    observation_id: str
    agent_id: str
    source_refs: tuple[str, ...]
    observed_at: str
    channel: str
    content: str
    uncertainty: float

    def __post_init__(self) -> None:
        for field_name in ("observation_id", "agent_id", "observed_at", "channel", "content"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must not be empty.")
        object.__setattr__(self, "source_refs", _source_refs(self.source_refs))
        if isinstance(self.uncertainty, bool) or not isinstance(self.uncertainty, (int, float)):
            raise TypeError("uncertainty must be a number between 0 and 1.")
        if not 0 <= self.uncertainty <= 1:
            raise ValueError("uncertainty must be between 0 and 1.")
        object.__setattr__(self, "uncertainty", float(self.uncertainty))
