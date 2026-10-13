from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze(item) for key, item in value.items()})
    if isinstance(value, (tuple, list)):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, set):
        return frozenset(_freeze(item) for item in value)
    return value


class ProposalType(str, Enum):
    CHARACTER_ACTION = "character_action"
    PLOT_DEVELOPMENT = "plot_development"
    WORLD_CHANGE = "world_change"


@dataclass(frozen=True)
class OpportunityProposal:
    """Unapproved possibility. It is not an event and carries no execution authority."""

    proposal_id: str
    proposal_type: ProposalType | str
    description: str
    related_entities: tuple[str, ...] = ()
    conditions: Mapping[str, Any] = field(default_factory=dict)
    confidence: float = 0.5
    possible_actions: tuple[str, ...] = ()
    source_character_id: str | None = None
    expires_at: str | None = None

    def __post_init__(self):
        for field_name in ("proposal_id", "description"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must not be empty.")
            object.__setattr__(self, field_name, value.strip())
        if not isinstance(self.proposal_type, ProposalType):
            object.__setattr__(self, "proposal_type", ProposalType(self.proposal_type))
        if isinstance(self.confidence, bool) or not isinstance(self.confidence, (int, float)) \
                or not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be between 0 and 1.")
        object.__setattr__(self, "confidence", float(self.confidence))
        entities = tuple(self.related_entities)
        actions = tuple(self.possible_actions)
        if any(not isinstance(item, str) or not item.strip() for item in (*entities, *actions)):
            raise ValueError("related_entities and possible_actions must contain non-empty strings.")
        if not isinstance(self.conditions, Mapping):
            raise TypeError("conditions must be a mapping.")
        if self.source_character_id is not None and not self.source_character_id.strip():
            raise ValueError("source_character_id must be None or non-empty.")
        if self.expires_at is not None and not self.expires_at.strip():
            raise ValueError("expires_at must be None or non-empty.")
        object.__setattr__(self, "related_entities", entities)
        object.__setattr__(self, "possible_actions", actions)
        object.__setattr__(self, "conditions", _freeze(self.conditions))


@dataclass(frozen=True)
class ProposalContext:
    """Explicitly public, immutable inputs permitted for proposal generation."""

    current_time: str
    location: str | None
    public_world_state: Mapping[str, Any]
    public_character_states: tuple[Mapping[str, Any], ...]
    recent_events: tuple[Mapping[str, Any], ...]
    public_conflicts: tuple[Mapping[str, Any], ...] = ()

    def __post_init__(self):
        if not isinstance(self.current_time, str):
            object.__setattr__(self, "current_time", str(self.current_time))
        if self.location is not None and not isinstance(self.location, str):
            raise TypeError("location must be a string or None.")
        if not isinstance(self.public_world_state, Mapping):
            raise TypeError("public_world_state must be a mapping.")
        if any(not isinstance(item, Mapping) for item in self.public_character_states):
            raise TypeError("public_character_states must contain mappings.")
        if any(not isinstance(item, Mapping) for item in self.recent_events):
            raise TypeError("recent_events must contain mappings.")
        if any(not isinstance(item, Mapping) for item in self.public_conflicts):
            raise TypeError("public_conflicts must contain mappings.")
        object.__setattr__(self, "public_world_state", _freeze(self.public_world_state))
        object.__setattr__(self, "public_character_states", tuple(_freeze(item) for item in self.public_character_states))
        object.__setattr__(self, "recent_events", tuple(_freeze(item) for item in self.recent_events))
        object.__setattr__(self, "public_conflicts", tuple(_freeze(item) for item in self.public_conflicts))

    @classmethod
    def from_public_data(cls, *, current_time, location=None, world_state=None,
                         character_states=(), recent_events=(), public_conflicts=()):
        """Build a provider-safe context using allowlists; private runtime objects are discarded."""
        world_allowed = {"world_id", "name", "description", "current_time", "day", "time",
                         "location", "current_location", "current_stage", "public_status", "public_locations",
                         "public_state"}
        character_allowed = {"character_id", "name", "role", "location", "availability",
                             "public_goal", "public_description", "visible_status"}
        event_allowed = {"event_id", "event_type", "timestamp", "location", "public_summary",
                         "description", "importance", "public_participants"}
        conflict_allowed = {"id", "type", "participants", "public_summary", "intensity", "pressure", "status"}
        world = {key: value for key, value in dict(world_state or {}).items() if key in world_allowed}
        characters = tuple({key: value for key, value in _public_mapping(item).items() if key in character_allowed}
                           for item in character_states)
        events = tuple(
            {key: value for key, value in _public_mapping(item).items() if key in event_allowed}
            for item in recent_events if _is_public_event(item)
        )
        conflicts = tuple(
            {key: value for key, value in _public_mapping(item).items() if key in conflict_allowed}
            for item in public_conflicts if _is_public_event(item)
        )
        return cls(str(current_time), location, world, characters, events, conflicts)


def _public_mapping(value):
    if isinstance(value, Mapping):
        return value
    fields = ("event_id", "event_type", "timestamp", "location", "public_summary", "description",
              "importance", "public_participants", "character_id", "name", "role", "availability",
              "public_goal", "public_description", "visible_status", "id", "type", "participants",
              "intensity", "pressure", "status")
    return {name: getattr(value, name) for name in fields if hasattr(value, name)}


def _is_public_event(value):
    if isinstance(value, Mapping):
        return (value.get("is_public") is True or value.get("visibility") == "public"
                or bool(value.get("public_summary")))
    return (getattr(value, "is_public", False) is True
            or getattr(value, "visibility", None) == "public"
            or bool(getattr(value, "public_summary", None)))
