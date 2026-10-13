from __future__ import annotations

from typing import Protocol, runtime_checkable

from .opportunity_proposal import OpportunityProposal, ProposalContext


@runtime_checkable
class OpportunityProposalProvider(Protocol):
    """Produces unapproved possibilities from a public, filtered context only."""

    def propose(self, context: ProposalContext) -> tuple[OpportunityProposal, ...]: ...


def validate_proposals(values) -> tuple[OpportunityProposal, ...]:
    proposals = tuple(values)
    if any(not isinstance(item, OpportunityProposal) for item in proposals):
        raise TypeError("proposal providers must return OpportunityProposal values, never events or opportunities.")
    return proposals
