from __future__ import annotations

from cognitive_sandbox.application.agent_context_builder import AgentContextBuilder
from cognitive_sandbox.application.character_card_validator import CharacterCardValidator
from cognitive_sandbox.application.event_card_validator import EventCardValidator
from cognitive_sandbox.application.scenario_validator import ScenarioValidator
from cognitive_sandbox.application.world_bootstrap import WorldBootstrap
from cognitive_sandbox.application.world_validator import WorldValidator
from cognitive_sandbox.domain.agent_context import AgentContext
from cognitive_sandbox.domain.character import CharacterState
from cognitive_sandbox.domain.character_card import CharacterCard
from cognitive_sandbox.domain.event_card import EventCard
from cognitive_sandbox.domain.scenario_content import ScenarioContent
from cognitive_sandbox.domain.scenario_runtime import AgentRuntimeProfile, ScenarioRuntime
from cognitive_sandbox.domain.validation_result import ValidationResult
from cognitive_sandbox.domain.world_state import WorldState


class ScenarioRuntimeBuilder:
    """Validate content first, then assemble detached runtime snapshots."""

    def __init__(
        self,
        world_bootstrap: WorldBootstrap | None = None,
        context_builder: AgentContextBuilder | None = None,
        *,
        scenario_validator: ScenarioValidator | None = None,
        world_validator: WorldValidator | None = None,
        character_validator: CharacterCardValidator | None = None,
        event_validator: EventCardValidator | None = None,
    ) -> None:
        self._world_bootstrap = world_bootstrap or WorldBootstrap()
        self._context_builder = context_builder or AgentContextBuilder()
        self._scenario_validator = scenario_validator or ScenarioValidator()
        self._world_validator = world_validator or WorldValidator()
        self._character_validator = character_validator or CharacterCardValidator()
        self._event_validator = event_validator or EventCardValidator()

    def validate(self, content: ScenarioContent) -> ValidationResult:
        if not isinstance(content, ScenarioContent):
            raise TypeError("content must be a ScenarioContent.")
        errors: list[str] = []
        scenario_result = self._scenario_validator.validate(content.scenario)
        errors.extend(f"scenario: {error}" for error in scenario_result.errors)

        if content.world_document is None:
            errors.append("world_document is required.")
        else:
            world_result = self._world_validator.validate(content.world_document)
            errors.extend(f"world_document: {error}" for error in world_result.errors)

        seen_character_ids: set[str] = set()
        for index, card in enumerate(content.character_cards):
            result = self._character_validator.validate(card)
            errors.extend(f"character_cards[{index}]: {error}" for error in result.errors)
            if card.character_id in seen_character_ids:
                errors.append(f"duplicate character card id: {card.character_id}")
            seen_character_ids.add(card.character_id)

        for index, card in enumerate(content.event_cards):
            result = self._event_validator.validate(card)
            errors.extend(f"event_cards[{index}]: {error}" for error in result.errors)

        return ValidationResult(not errors, tuple(errors), ())

    def build(self, content: ScenarioContent) -> ScenarioRuntime:
        self._validate_or_raise(content)
        # No runtime object is made visible to callers until every validation passes.
        world_state = self._build_world(content)
        agents = self._build_agents(content, world_state)
        initial_events = self._collect_events(content)
        return ScenarioRuntime(
            scenario_id=content.scenario.scenario_id,
            world_state=world_state,
            agents=agents,
            initial_events=initial_events,
        )

    def build_world(self, content: ScenarioContent) -> WorldState:
        self._validate_or_raise(content)
        return self._build_world(content)

    def build_agents(
        self,
        content: ScenarioContent,
        world_state: WorldState | None = None,
    ) -> tuple[AgentRuntimeProfile, ...]:
        self._validate_or_raise(content)
        selected_world = world_state or self._build_world(content)
        if not isinstance(selected_world, WorldState):
            raise TypeError("world_state must be a WorldState.")
        return self._build_agents(content, selected_world)

    def collect_events(self, content: ScenarioContent) -> tuple[EventCard, ...]:
        self._validate_or_raise(content)
        return self._collect_events(content)

    def _build_world(self, content: ScenarioContent) -> WorldState:
        return self._world_bootstrap.create_world_from_document(
            content.world_document,
            content.scenario.initial_world_state,
        )

    def _build_agents(
        self,
        content: ScenarioContent,
        world_state: WorldState,
    ) -> tuple[AgentRuntimeProfile, ...]:
        profiles: list[AgentRuntimeProfile] = []
        for card in content.character_cards:
            character = CharacterState(
                character_id=card.character_id,
                name=card.name,
                role=card.occupation or "character",
                traits=card.personality,
                goals=card.goals,
                fears=(),
                memories=(),
            )
            context: AgentContext = self._context_builder.build(
                character,
                memories=(),
                relationships=(),
                world_state=world_state.state,
            )
            profiles.append(AgentRuntimeProfile(context, card.constraints))
        return tuple(profiles)

    @staticmethod
    def _collect_events(content: ScenarioContent) -> tuple[EventCard, ...]:
        return tuple(content.event_cards)

    def _validate_or_raise(self, content: ScenarioContent) -> None:
        result = self.validate(content)
        if not result.valid:
            raise ValueError("scenario content validation failed: " + "; ".join(result.errors))
