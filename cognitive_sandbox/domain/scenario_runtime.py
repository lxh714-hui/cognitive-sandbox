from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

from cognitive_sandbox.domain.agent_context import AgentContext
from cognitive_sandbox.domain.constraint import Constraint
from cognitive_sandbox.domain.event_card import EventCard
from cognitive_sandbox.domain.world_state import WorldState
from cognitive_sandbox.domain.character_card import CharacterCard
from cognitive_sandbox.domain.world_document import WorldDocument


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise TypeError("runtime mapping keys must be strings.")
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(_freeze(item) for item in value)
    return value


@dataclass(frozen=True)
class AgentRuntimeProfile:
    """Runtime context plus static constraints carried from its character card."""

    agent_context: AgentContext
    constraints: tuple[Constraint, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.agent_context, AgentContext):
            raise TypeError("agent_context must be an AgentContext.")
        if isinstance(self.constraints, (str, bytes)):
            raise TypeError("constraints must be a collection of Constraint values.")
        constraints = tuple(self.constraints)
        if any(not isinstance(item, Constraint) for item in constraints):
            raise TypeError("constraints must contain only Constraint values.")
        object.__setattr__(self, "constraints", constraints)

    @property
    def agent_id(self) -> str:
        return self.agent_context.character_id


@dataclass(frozen=True)
class ScenarioRuntime:
    """Immutable contract handed from a package boundary to generic runtime services."""

    scenario_id: str
    world_state: WorldState
    agents: tuple[AgentRuntimeProfile, ...]
    initial_events: tuple[EventCard, ...]
    version: str = "1"
    metadata: Mapping[str, Any] = field(default_factory=dict)
    entities: tuple[Mapping[str, Any], ...] = ()
    rules: tuple[Mapping[str, Any], ...] = ()
    assets: Mapping[str, Any] = field(default_factory=dict)
    configuration: Mapping[str, Any] = field(default_factory=dict)
    character_cards: tuple[CharacterCard, ...] = ()
    world_document: WorldDocument | None = None
    cognitive_rules: tuple[Mapping[str, Any], ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.scenario_id, str) or not self.scenario_id.strip():
            raise ValueError("scenario_id must not be empty.")
        if not isinstance(self.world_state, WorldState):
            raise TypeError("world_state must be a WorldState.")
        agents = tuple(self.agents)
        events = tuple(self.initial_events)
        if any(not isinstance(agent, AgentRuntimeProfile) for agent in agents):
            raise TypeError("agents must contain AgentRuntimeProfile values.")
        if any(not isinstance(event, EventCard) for event in events):
            raise TypeError("initial_events must contain EventCard values.")
        object.__setattr__(self, "agents", agents)
        object.__setattr__(self, "initial_events", events)
        if not isinstance(self.version, str):
            raise TypeError("version must be a string.")
        if not self.version.strip():
            raise ValueError("version must not be empty.")
        for name in ("metadata", "assets", "configuration"):
            value = getattr(self, name)
            if value is None:
                value = {}
            if not isinstance(value, Mapping):
                raise TypeError(f"{name} must be a mapping.")
            object.__setattr__(self, name, _freeze(value))
        entities = tuple(_freeze(item) for item in self.entities)
        rules = tuple(_freeze(item) for item in self.rules)
        if any(not isinstance(item, Mapping) for item in entities):
            raise TypeError("entities must contain mappings.")
        if any(not isinstance(item, Mapping) for item in rules):
            raise TypeError("rules must contain mappings.")
        object.__setattr__(self, "entities", entities)
        object.__setattr__(self, "rules", rules)
        source_cognitive_rules = self.cognitive_rules
        if not source_cognitive_rules:
            source_cognitive_rules = self.configuration.get("cognitive_rules", ())
        cognitive_rules = tuple(_freeze(item) for item in source_cognitive_rules)
        if any(not isinstance(item, Mapping) for item in cognitive_rules):
            raise TypeError("cognitive_rules must contain mappings.")
        from cognitive_sandbox.cognition.cognitive_rule_provider import CognitiveRuleProvider
        errors = CognitiveRuleProvider.validate(cognitive_rules)
        if errors:
            raise ValueError("invalid cognitive rules: " + "; ".join(errors))
        object.__setattr__(self, "cognitive_rules", cognitive_rules)
        cards = tuple(self.character_cards)
        if any(not isinstance(card, CharacterCard) for card in cards):
            raise TypeError("character_cards must contain CharacterCard values.")
        object.__setattr__(self, "character_cards", cards)
        if self.world_document is not None and not isinstance(self.world_document, WorldDocument):
            raise TypeError("world_document must be a WorldDocument or None.")

    @property
    def agent_contexts(self) -> tuple[AgentContext, ...]:
        return tuple(agent.agent_context for agent in self.agents)
