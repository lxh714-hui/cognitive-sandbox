from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from datetime import datetime
from collections.abc import Mapping
from types import MappingProxyType
from typing import Any

from cognitive_sandbox.domain.actions import ActionCandidate


class OpportunitySourceType(str, Enum):
    GOAL = "GOAL"
    CONFLICT = "CONFLICT"
    INFORMATION = "INFORMATION"
    RELATIONSHIP = "RELATIONSHIP"
    WORLD = "WORLD"
    AI_PROPOSAL = "AI_PROPOSAL"
    WORLD_RULE = "WORLD_RULE"
    NPC_AGENCY = "NPC_AGENCY"


class OpportunityStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    RESOLVED = "resolved"


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, set):
        return frozenset(_freeze(item) for item in value)
    return value


@dataclass(frozen=True)
class NarrativeOpportunity:
    """A visible possibility to consider; it is not an event or command."""

    opportunity_id: str
    source_type: OpportunitySourceType | str
    related_goal: str | None = None
    related_conflict: str | None = None
    related_character: str | None = None
    visibility: str = "owner"
    urgency: float = 0.0
    importance: float = 0.0
    possible_actions: tuple[str, ...] = ()
    created_time: str = ""
    expiry: str | None = None
    description: str = ""
    visible_character_ids: tuple[str, ...] = ()
    suggested_granularity: str = "normal"
    source: str = "world_rule"
    source_id: str | None = None
    internal_context: Mapping[str, Any] = None
    related_entities: tuple[str, ...] = ()
    candidate_actions: tuple[ActionCandidate, ...] = ()
    status: OpportunityStatus | str = OpportunityStatus.ACTIVE

    def __post_init__(self):
        if not isinstance(self.opportunity_id, str) or not self.opportunity_id.strip():
            raise ValueError("opportunity_id must not be empty.")
        if not isinstance(self.source_type, OpportunitySourceType):
            object.__setattr__(self, "source_type", OpportunitySourceType(self.source_type))
        if not isinstance(self.status, OpportunityStatus):
            object.__setattr__(self, "status", OpportunityStatus(self.status))
        for name in ("related_goal", "related_conflict", "related_character", "expiry", "source_id"):
            value = getattr(self, name)
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise ValueError(f"{name} must be None or a non-empty string.")
        for name in ("visibility", "created_time", "description", "suggested_granularity"):
            value = getattr(self, name)
            if not isinstance(value, str):
                raise TypeError(f"{name} must be a string.")
        if not self.description.strip():
            raise ValueError("description must not be empty.")
        if self.visibility not in {"public", "owner", "participants", "private"}:
            raise ValueError("visibility must be public, owner, participants, or private.")
        for name in ("urgency", "importance"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1:
                raise ValueError(f"{name} must be between 0 and 1.")
            object.__setattr__(self, name, float(value))
        actions = tuple(self.possible_actions)
        visible = tuple(self.visible_character_ids)
        entities = tuple(self.related_entities)
        candidates = tuple(self.candidate_actions)
        if any(not isinstance(item, str) or not item.strip() for item in (*actions, *visible)):
            raise ValueError("possible_actions and visible_character_ids must contain non-empty strings.")
        if any(not isinstance(item, str) or not item.strip() for item in entities):
            raise ValueError("related_entities must contain non-empty strings.")
        if any(not isinstance(item, ActionCandidate) for item in candidates):
            raise TypeError("candidate_actions must contain ActionCandidate values.")
        if not isinstance(self.source, str) or not self.source.strip():
            raise ValueError("source must not be empty.")
        source = self.source.strip().casefold().replace(" ", "_")
        if source not in {"ai_proposal", "world_rule", "npc_agency"}:
            raise ValueError("source must be ai_proposal, world_rule, or npc_agency.")
        object.__setattr__(self, "source", source)
        context = {} if self.internal_context is None else self.internal_context
        if not isinstance(context, Mapping):
            raise TypeError("internal_context must be a mapping.")
        object.__setattr__(self, "internal_context", _freeze(context))
        object.__setattr__(self, "possible_actions", actions)
        object.__setattr__(self, "visible_character_ids", visible)
        object.__setattr__(self, "related_entities", entities)
        object.__setattr__(self, "candidate_actions", candidates)

    @property
    def id(self) -> str:
        return self.opportunity_id

    @property
    def expiration(self) -> str | None:
        return self.expiry

    def is_visible_to(self, character_id: str) -> bool:
        if not isinstance(character_id, str) or not character_id.strip() or self.visibility == "private":
            return False
        if self.visibility == "public":
            return True
        return character_id in self.visible_character_ids

    def is_expired(self, current_time=None) -> bool:
        # Expiration is evaluated against world time only; wall-clock time must
        # not expire an opportunity in a paused or replayed simulation.
        if self.status is not OpportunityStatus.ACTIVE or not self.expiry or current_time is None:
            return False
        try:
            expires = datetime.fromisoformat(self.expiry.replace("Z", "+00:00"))
            now = current_time if hasattr(current_time, "tzinfo") else datetime.fromisoformat(
                str(current_time).replace("Z", "+00:00")
            )
            if now.tzinfo is None and expires.tzinfo is not None:
                now = now.replace(tzinfo=expires.tzinfo)
            if expires.tzinfo is None and now.tzinfo is not None:
                expires = expires.replace(tzinfo=now.tzinfo)
            return now >= expires
        except (AttributeError, TypeError, ValueError):
            return False
