from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Protocol


def _freeze(value):
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise TypeError("proposal mapping keys must be strings")
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, (tuple, list)):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(_freeze(item) for item in value)
    return value


@dataclass(frozen=True)
class Proposal:
    """Unapproved candidate content. It is data only and cannot mutate a world."""

    proposal_id: str
    proposal_type: str
    source: str
    payload: Mapping = field(default_factory=dict)
    confidence: float = 0.0

    def __post_init__(self):
        for name in ("proposal_id", "proposal_type", "source"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must not be empty")
        if not isinstance(self.payload, Mapping):
            raise TypeError("payload must be a mapping")
        if isinstance(self.confidence, bool) or not isinstance(self.confidence, (int, float)):
            raise TypeError("confidence must be numeric")
        if not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")
        object.__setattr__(self, "payload", _freeze(self.payload))


class ProposalProvider(Protocol):
    """Providers suggest immutable candidates and receive only an explicit view."""

    def propose(self, public_context: Mapping) -> tuple[Proposal, ...]: ...


class ProposalValidator(Protocol):
    """Validate a proposal against public runtime rules before any approval."""

    def validate(self, proposal: Proposal, runtime) -> object: ...


class ProposalApprover(Protocol):
    """Explicit approval boundary; providers cannot approve their own output."""

    def approve(self, proposal: Proposal, *, approver_id: str) -> bool: ...
