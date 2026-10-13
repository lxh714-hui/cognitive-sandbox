from __future__ import annotations

from collections.abc import Mapping
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
        config = content.scenario.runtime_config
        entities = tuple(
            {"id": card.character_id, "kind": "entity", "name": card.name}
            for card in content.character_cards
        )
        entities += tuple(
            {"id": item["location_id"], "kind": "location", "name": item.get("name", item["location_id"])}
            for item in config.get("locations", ())
            if isinstance(item, Mapping) and isinstance(item.get("location_id"), str)
        )
        for kind, collection_key, id_keys in (
            ("entity", "entities", ("entity_id", "id")),
            ("item", "items", ("item_id", "id")),
            ("resource", "resources", ("resource_id", "resource_type", "id")),
        ):
            for item in config.get(collection_key, ()):
                if not isinstance(item, Mapping):
                    continue
                identity = next((item.get(key) for key in id_keys if isinstance(item.get(key), str)), None)
                if identity:
                    entities += ({"id": identity, "kind": kind, **dict(item)},)
        metadata = {
            "name": content.scenario.name,
            "description": content.scenario.description,
            "world_id": content.world_document.world_id,
        }
        return ScenarioRuntime(
            scenario_id=content.scenario.scenario_id,
            world_state=world_state,
            agents=agents,
            initial_events=initial_events,
            version=str(config.get("package_version") or config.get("version") or "1"),
            metadata=metadata,
            entities=entities,
            rules=tuple(config.get("evolution_rules", ())),
            assets=config.get("assets", {}),
            configuration=config,
            character_cards=content.character_cards,
            world_document=content.world_document,
            cognitive_rules=tuple(config.get("cognitive_rules", ())),
        )

    def build_scenario(self, scenario) -> ScenarioRuntime:
        """Adapt a legacy in-memory scenario to the same generic runtime contract."""
        from cognitive_sandbox.domain.scenario import Scenario

        if not isinstance(scenario, Scenario):
            raise TypeError("scenario must be a Scenario.")
        world = self._world_bootstrap.create(scenario).world_state
        contexts = []
        for item in scenario.character_templates:
            identity = item.get("character_id", item.get("id"))
            if not isinstance(identity, str) or not identity.strip():
                continue
            character = CharacterState(
                character_id=identity,
                name=str(item.get("name", identity)),
                role=str(item.get("role", "character")),
                traits=tuple(item.get("traits", ())),
                goals=tuple(item.get("goals", ())),
            )
            contexts.append(self._context_builder.build(
                character, memories=(), relationships=(), world_state=world.state,
            ))
        entities = tuple(dict(item) for item in scenario.character_templates)
        return ScenarioRuntime(
            scenario_id=scenario.scenario_id,
            world_state=world,
            agents=tuple(AgentRuntimeProfile(item) for item in contexts),
            initial_events=(),
            version=str(scenario.runtime_config.get("package_version") or scenario.runtime_config.get("version") or "1"),
            metadata={"name": scenario.name, "description": scenario.description},
            entities=entities,
            rules=tuple(scenario.runtime_config.get("evolution_rules", ())),
            assets=scenario.runtime_config.get("assets", {}),
            configuration=scenario.runtime_config,
            cognitive_rules=tuple(scenario.runtime_config.get("cognitive_rules", ())),
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
