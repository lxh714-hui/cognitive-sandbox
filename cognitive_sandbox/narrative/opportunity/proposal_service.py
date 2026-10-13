from __future__ import annotations

from dataclasses import dataclass
from cognitive_sandbox.domain.actions import ActionCandidate

from .narrative_opportunity import NarrativeOpportunity, OpportunitySourceType
from .opportunity_proposal import OpportunityProposal, ProposalContext, ProposalType
from .opportunity_proposal_provider import validate_proposals
from .proposal_validation import ProposalValidationResult, ProposalValidator


@dataclass(frozen=True)
class ProposalApproval:
    proposal: OpportunityProposal
    validation: ProposalValidationResult
    opportunity: NarrativeOpportunity | None = None
    world_tree_branches: tuple = ()

    @property
    def approved(self) -> bool:
        return self.validation.valid and self.opportunity is not None


class OpportunityProposalService:
    """Keeps proposals inert until explicit approval, then registers an opportunity."""

    def __init__(self, provider, *, validator=None):
        if not callable(getattr(provider, "propose", None)):
            raise TypeError("provider must implement propose(context).")
        self.provider = provider
        self.validator = validator or ProposalValidator()
        self._pending: dict[str, OpportunityProposal] = {}

    @property
    def pending(self) -> tuple[OpportunityProposal, ...]:
        return tuple(self._pending.values())

    def generate(self, context: ProposalContext) -> tuple[OpportunityProposal, ...]:
        if not isinstance(context, ProposalContext):
            raise TypeError("generate requires a sanitized ProposalContext.")
        proposals = validate_proposals(self.provider.propose(context))
        for proposal in proposals:
            self._pending[proposal.proposal_id] = proposal
        return proposals

    def validate(self, proposal: OpportunityProposal, context: ProposalContext) -> ProposalValidationResult:
        return self.validator.validate(proposal, context)

    def approve(self, proposal_id: str, context: ProposalContext, *, opportunity_service,
                world_tree_manager=None) -> ProposalApproval:
        proposal = self._pending.get(proposal_id)
        if proposal is None:
            raise KeyError(f"No pending proposal: {proposal_id}")
        validation = self.validator.validate(proposal, context)
        if not validation.valid:
            return ProposalApproval(proposal, validation)
        opportunity = proposal_to_opportunity(proposal, context)
        opportunity_service.register(opportunity)
        branches = tuple(world_tree_manager.register_opportunity(opportunity)) if world_tree_manager else ()
        self._pending.pop(proposal_id, None)
        return ProposalApproval(proposal, validation, opportunity, branches)


def proposal_to_opportunity(proposal: OpportunityProposal, context: ProposalContext) -> NarrativeOpportunity:
    character_ids = {str(item.get("character_id")) for item in context.public_character_states
                     if item.get("character_id")}
    target = proposal.source_character_id or next(
        (item.partition(":")[2] for item in proposal.related_entities
         if item.startswith("character:") and item.partition(":")[2] in character_ids), None,
    )
    is_npc_candidate = proposal.proposal_type is ProposalType.CHARACTER_ACTION and target is not None
    candidates = ()
    if is_npc_candidate:
        candidates = tuple(_action_candidate(target, action, proposal) for action in proposal.possible_actions)
        # A character-action proposal with no explicit candidate remains descriptive, never executable.
    return NarrativeOpportunity(
        opportunity_id=f"proposal_{proposal.proposal_id}",
        source_type=OpportunitySourceType.AI_PROPOSAL,
        related_character=target,
        visibility="owner" if is_npc_candidate else "public",
        urgency=0.0,
        importance=proposal.confidence,
        possible_actions=proposal.possible_actions,
        created_time=context.current_time,
        expiry=proposal.expires_at,
        description=proposal.description,
        visible_character_ids=(target,) if is_npc_candidate else tuple(character_ids),
        source="ai_proposal",
        source_id=proposal.proposal_id,
        internal_context={"conditions": dict(proposal.conditions), "proposal_type": proposal.proposal_type.value},
        related_entities=proposal.related_entities,
        candidate_actions=candidates,
    )


def _action_candidate(actor_id, label, proposal):
    lowered = label.casefold()
    action_type = next((action for tokens, action in (
        (("调查", "探查", "寻找"), "investigate"), (("询问", "交谈", "联系"), "ask"),
        (("观察", "留意"), "observe"), (("前往", "去"), "travel"),
        (("帮助", "协助"), "help"), (("等待", "暂缓"), "rest"),
    ) if any(token in lowered for token in tokens)), "observe")
    return ActionCandidate(
        action_type=action_type, intent=action_type, actor_id=actor_id,
        motivation="approved_ai_opportunity",
        metadata={"objective": f"proposal:{proposal.proposal_id}", "method": action_type,
                  "expected_effect": action_type, "opportunity_proposal_id": proposal.proposal_id},
    )
