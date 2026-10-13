from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .opportunity_proposal import OpportunityProposal, ProposalContext, ProposalType


@dataclass(frozen=True)
class ProposalValidationResult:
    valid: bool
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


class ProposalValidator:
    """Checks public consistency and narrative value without mutating runtime state."""

    _noise_terms = ("吃饭", "上班", "整理房间", "普通地休息", "日常走路")
    _secret_terms = ("隐藏知识", "秘密真相", "完整世界事实", "hidden_fact", "secret_knowledge")

    def __init__(self, *, minimum_confidence: float = 0.35):
        if not 0 <= minimum_confidence <= 1:
            raise ValueError("minimum_confidence must be between 0 and 1.")
        self.minimum_confidence = minimum_confidence

    def validate(self, proposal: OpportunityProposal, context: ProposalContext) -> ProposalValidationResult:
        if not isinstance(proposal, OpportunityProposal) or not isinstance(context, ProposalContext):
            raise TypeError("validate requires an OpportunityProposal and ProposalContext.")
        errors = []
        warnings = []
        characters = {str(item.get("character_id")): item for item in context.public_character_states
                      if item.get("character_id")}
        locations = _known_locations(context)
        for entity in proposal.related_entities:
            kind, _, identifier = entity.partition(":")
            if not identifier:
                identifier = kind
                kind = ""
            if kind == "character" or (not kind and identifier in characters):
                if identifier not in characters:
                    errors.append(f"unknown or unavailable character: {identifier}")
            elif kind == "location" or (not kind and identifier in locations):
                if identifier not in locations:
                    errors.append(f"unknown location: {identifier}")
            elif not kind:
                errors.append(f"unknown or unavailable entity: {identifier}")
            elif kind:
                errors.append(f"unsupported entity reference: {entity}")
        if proposal.source_character_id and proposal.source_character_id not in characters:
            errors.append("proposal character is not present in the public character context")
        proposed_location = proposal.conditions.get("location")
        if proposed_location and proposed_location not in locations:
            errors.append(f"unknown location: {proposed_location}")
        if not _time_is_possible(proposal.conditions, context.current_time):
            errors.append("proposal time conditions are inconsistent with current world time")
        searchable = " ".join((proposal.description, *proposal.related_entities, *proposal.possible_actions,
                               str(dict(proposal.conditions)))).casefold()
        if any(term.casefold() in searchable for term in self._secret_terms):
            errors.append("proposal appears to disclose hidden information")
        if proposal.confidence < self.minimum_confidence:
            warnings.append("proposal confidence is below the preferred threshold")
        if len(proposal.description.strip()) < 12:
            warnings.append("proposal has too little detail to offer a meaningful narrative choice")
        if any(term in proposal.description for term in self._noise_terms) and not proposal.conditions:
            warnings.append("ordinary routine activity has little narrative value without additional context")
        if warnings and (proposal.confidence < self.minimum_confidence or
                         any("little narrative value" in item for item in warnings)):
            errors.extend(warnings)
            warnings.clear()
        return ProposalValidationResult(not errors, tuple(errors), tuple(warnings))


def _known_locations(context):
    values = set()
    for key in ("location", "current_location"):
        item = context.public_world_state.get(key)
        if isinstance(item, str):
            values.add(item)
    extra = context.public_world_state.get("public_locations", ())
    if isinstance(extra, (list, tuple, set, frozenset)):
        values.update(str(item) for item in extra)
    for character in context.public_character_states:
        if character.get("location"):
            values.add(str(character["location"]))
    return values


def _time_is_possible(conditions: Any, current_time: str) -> bool:
    if not isinstance(conditions, dict) and not hasattr(conditions, "get"):
        return False
    try:
        now = datetime.fromisoformat(str(current_time).replace("Z", "+00:00"))
    except ValueError:
        return True  # Unknown clock format cannot establish a contradiction.
    for field, comparison in (("not_before", lambda bound: now >= bound),
                              ("not_after", lambda bound: now <= bound)):
        value = conditions.get(field)
        if value:
            try:
                bound = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
                if now.tzinfo is None and bound.tzinfo is not None:
                    now = now.replace(tzinfo=bound.tzinfo)
                if bound.tzinfo is None and now.tzinfo is not None:
                    bound = bound.replace(tzinfo=now.tzinfo)
                if not comparison(bound):
                    return False
            except ValueError:
                return False
    return True
