from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any, Protocol

from cognitive_sandbox.application.character_card_validator import CharacterCardValidator
from cognitive_sandbox.application.event_card_validator import EventCardValidator
from cognitive_sandbox.application.prompts.world_generation_prompt import (
    build_world_generation_prompt,
)
from cognitive_sandbox.application.scenario_validator import ScenarioValidator
from cognitive_sandbox.application.world_validator import WorldValidator
from cognitive_sandbox.domain.ai_gm import AIGMRequest, AIGMResponse
from cognitive_sandbox.domain.character_card import CharacterCard
from cognitive_sandbox.domain.constraint import Constraint
from cognitive_sandbox.domain.event_card import EventCard
from cognitive_sandbox.domain.scenario import Scenario
from cognitive_sandbox.domain.scenario_content import ScenarioContent
from cognitive_sandbox.domain.validation_result import ValidationResult
from cognitive_sandbox.domain.world_document import WorldDocument
from cognitive_sandbox.domain.world_generation_result import WorldGenerationResult


class WorldGenerationProvider(Protocol):
    def complete(self, request: AIGMRequest) -> AIGMResponse: ...


class WorldGenerator:
    """Generate and validate content drafts without constructing runtime state."""

    ROOT_FIELDS = frozenset({"world", "characters", "events"})
    WORLD_FIELDS = frozenset({"world_id", "name", "description", "history", "rules"})
    CHARACTER_FIELDS = frozenset(
        {"character_id", "name", "identity", "personality", "background", "goals", "constraints"}
    )
    IDENTITY_FIELDS = frozenset({"age", "gender", "occupation", "portrait"})
    EVENT_FIELDS = frozenset(
        {"event_id", "name", "description", "event_type", "participants", "conditions", "effects", "priority"}
    )

    def __init__(
        self,
        provider: WorldGenerationProvider,
        *,
        world_validator: WorldValidator | None = None,
        character_validator: CharacterCardValidator | None = None,
        event_validator: EventCardValidator | None = None,
        scenario_validator: ScenarioValidator | None = None,
        min_characters: int = 3,
        max_characters: int = 5,
        min_events: int = 1,
        max_events: int = 3,
    ) -> None:
        if not callable(getattr(provider, "complete", None)):
            raise TypeError("provider must provide a callable complete method.")
        for name, value in (
            ("min_characters", min_characters),
            ("max_characters", max_characters),
            ("min_events", min_events),
            ("max_events", max_events),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer.")
        if min_characters > max_characters or min_events > max_events:
            raise ValueError("minimum counts cannot exceed maximum counts.")
        self._provider = provider
        self._world_validator = world_validator or WorldValidator()
        self._character_validator = character_validator or CharacterCardValidator()
        self._event_validator = event_validator or EventCardValidator()
        self._scenario_validator = scenario_validator or ScenarioValidator()
        self._min_characters = min_characters
        self._max_characters = max_characters
        self._min_events = min_events
        self._max_events = max_events

    def generate(self, user_prompt: str) -> WorldGenerationResult:
        if not isinstance(user_prompt, str) or not user_prompt.strip():
            return self._failure("user_prompt must not be empty.")

        prompt = build_world_generation_prompt(
            user_prompt,
            min_characters=self._min_characters,
            max_characters=self._max_characters,
            min_events=self._min_events,
            max_events=self._max_events,
        )
        try:
            response = self._provider.complete(
                AIGMRequest("generate_world", {"prompt": prompt})
            )
        except Exception as error:
            return self._failure(f"world generation provider failed: {self._message(error)}")
        if not isinstance(response, AIGMResponse):
            return self._failure("world generation provider returned an invalid response type.")
        if not response.success or response.content.startswith("LLM provider error:"):
            return self._failure(f"world generation provider failed ({response.error}).")

        try:
            content = self._parse_content(response.content)
        except (TypeError, ValueError, KeyError) as error:
            return self._failure(f"invalid world generation output: {self._message(error)}")

        validation = self._validate(content)
        if not validation.valid:
            return WorldGenerationResult(
                scenario_content=None,
                validation_result=validation,
                warnings=validation.warnings,
                error="generated world content failed validation: " + "; ".join(validation.errors),
            )

        warnings = (
            "草稿尚未运行模拟；事件卡描述的是可能内容，不代表已发生的结果。",
        )
        return WorldGenerationResult(
            scenario_content=content,
            validation_result=ValidationResult(True, (), warnings),
            warnings=warnings,
        )

    def _parse_content(self, raw: str) -> ScenarioContent:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as error:
            raise ValueError(f"response is not strict JSON ({error.msg}).") from error
        root = _object(data, "root")
        _require_fields(root, self.ROOT_FIELDS, "root")

        world_data = _object(root["world"], "world")
        _require_fields(world_data, self.WORLD_FIELDS, "world")
        world = WorldDocument(
            world_id=world_data["world_id"],
            name=world_data["name"],
            description=world_data["description"],
            history=_array(world_data["history"], "world.history"),
            rules=_array(world_data["rules"], "world.rules"),
        )

        raw_characters = _array(root["characters"], "characters")
        characters: list[CharacterCard] = []
        for index, raw_character in enumerate(raw_characters):
            label = f"characters[{index}]"
            character = _object(raw_character, label)
            _require_fields(character, self.CHARACTER_FIELDS, label)
            identity = _object(character["identity"], f"{label}.identity")
            unexpected_identity = sorted(identity.keys() - self.IDENTITY_FIELDS)
            if unexpected_identity:
                raise ValueError(
                    f"{label}.identity has unexpected fields: {', '.join(unexpected_identity)}"
                )
            raw_constraints = _array(character["constraints"], f"{label}.constraints")
            constraints: list[Constraint] = []
            for constraint_index, raw_constraint in enumerate(raw_constraints):
                constraint_label = f"{label}.constraints[{constraint_index}]"
                constraint = _object(raw_constraint, constraint_label)
                _require_fields(constraint, frozenset({"type", "content"}), constraint_label)
                constraints.append(Constraint(constraint["type"], constraint["content"]))
            characters.append(
                CharacterCard(
                    character_id=character["character_id"],
                    name=character["name"],
                    age=identity.get("age"),
                    gender=identity.get("gender", ""),
                    occupation=identity.get("occupation", ""),
                    portrait=identity.get("portrait"),
                    personality=_array(character["personality"], f"{label}.personality"),
                    background=character["background"],
                    goals=_array(character["goals"], f"{label}.goals"),
                    constraints=tuple(constraints),
                )
            )

        raw_events = _array(root["events"], "events")
        events: list[EventCard] = []
        for index, raw_event in enumerate(raw_events):
            label = f"events[{index}]"
            event = _object(raw_event, label)
            _require_fields(event, self.EVENT_FIELDS, label)
            events.append(
                EventCard(
                    event_id=event["event_id"],
                    name=event["name"],
                    description=event["description"],
                    event_type=event["event_type"],
                    participants=_array(event["participants"], f"{label}.participants"),
                    conditions=_array(event["conditions"], f"{label}.conditions"),
                    effects=_array(event["effects"], f"{label}.effects"),
                    priority=event["priority"],
                )
            )

        # ScenarioContent includes a runtime Scenario for package compatibility.
        # This deterministic placeholder is data only; no runtime is constructed here.
        scenario = Scenario(
            scenario_id=world.world_id,
            name=world.name,
            description=world.description,
            initial_world_state={"world_id": world.world_id},
            character_templates=tuple(
                {
                    "id": card.character_id,
                    "name": card.name,
                    "role": card.occupation or "character",
                    "traits": card.personality,
                    "goals": card.goals,
                }
                for card in characters
            ),
        )
        return ScenarioContent(
            scenario=scenario,
            world_document=world,
            character_cards=tuple(characters),
            event_cards=tuple(events),
        )

    def _validate(self, content: ScenarioContent) -> ValidationResult:
        errors: list[str] = []
        warnings: list[str] = []
        assert content.world_document is not None
        world_result = self._world_validator.validate(content.world_document)
        errors.extend(f"world: {item}" for item in world_result.errors)
        warnings.extend(world_result.warnings)

        if not self._min_characters <= len(content.character_cards) <= self._max_characters:
            errors.append(
                f"characters must contain between {self._min_characters} and "
                f"{self._max_characters} cards."
            )
        seen_ids: set[str] = set()
        for index, card in enumerate(content.character_cards):
            result = self._character_validator.validate(card)
            errors.extend(f"characters[{index}]: {item}" for item in result.errors)
            warnings.extend(result.warnings)
            if card.character_id in seen_ids:
                errors.append(f"duplicate character id: {card.character_id}")
            seen_ids.add(card.character_id)

        if not self._min_events <= len(content.event_cards) <= self._max_events:
            errors.append(
                f"events must contain between {self._min_events} and {self._max_events} cards."
            )
        seen_event_ids: set[str] = set()
        for index, card in enumerate(content.event_cards):
            result = self._event_validator.validate(card)
            errors.extend(f"events[{index}]: {item}" for item in result.errors)
            warnings.extend(result.warnings)
            if card.event_id in seen_event_ids:
                errors.append(f"duplicate event id: {card.event_id}")
            seen_event_ids.add(card.event_id)

        scenario_result = self._scenario_validator.validate(content.scenario)
        errors.extend(f"scenario: {item}" for item in scenario_result.errors)
        warnings.extend(scenario_result.warnings)

        forbidden = _find_forbidden_outcome(content)
        errors.extend(forbidden)
        return ValidationResult(not errors, tuple(errors), tuple(warnings))

    @staticmethod
    def _message(error: Exception) -> str:
        message = str(error).strip()
        return message or error.__class__.__name__

    @staticmethod
    def _failure(message: str) -> WorldGenerationResult:
        validation = ValidationResult(False, (message,), ())
        return WorldGenerationResult(None, validation, (), message)


def _object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object.")
    return value


def _array(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be a JSON array.")
    return value


def _require_fields(data: Mapping[str, Any], required: frozenset[str], label: str) -> None:
    missing = sorted(required - data.keys())
    unexpected = sorted(data.keys() - required)
    details: list[str] = []
    if missing:
        details.append("missing fields: " + ", ".join(missing))
    if unexpected:
        details.append("unexpected fields: " + ", ".join(unexpected))
    if details:
        raise ValueError(f"{label} has invalid fields (" + "; ".join(details) + ").")


def _find_forbidden_outcome(content: ScenarioContent) -> tuple[str, ...]:
    forbidden_phrases = (
        "玩家一定成功",
        "角色一定死亡",
        "玩家必定成功",
        "角色必定死亡",
        "the player will definitely succeed",
        "the character will definitely die",
    )
    values: list[str] = []
    world = content.world_document
    if world is not None:
        values.extend((world.name, world.description, *world.history, *world.rules))
    for card in content.character_cards:
        values.extend((card.name, card.occupation, card.background, *card.personality, *card.goals))
        values.extend(constraint.content for constraint in card.constraints)
    for card in content.event_cards:
        values.extend((card.name, card.description, *card.conditions, *card.effects))
    found = sorted({phrase for phrase in forbidden_phrases if any(phrase in value.casefold() for value in values)})
    return tuple(f"content contains prohibited guaranteed outcome: {phrase}" for phrase in found)
