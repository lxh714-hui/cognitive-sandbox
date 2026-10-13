from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from cognitive_sandbox.domain.scenario import Scenario
from cognitive_sandbox.domain.validation_result import ValidationResult
from cognitive_sandbox.application.scenario_rule_resolver import validate_rule_collection
from cognitive_sandbox.cognition.cognitive_rule_provider import CognitiveRuleProvider


class ScenarioValidator:
    """Read-only structural checks performed before world bootstrap."""

    def validate(self, scenario: Scenario) -> ValidationResult:
        if not isinstance(scenario, Scenario):
            raise TypeError("scenario must be a Scenario.")

        errors: list[str] = []
        warnings: list[str] = []
        for field_name in ("scenario_id", "name", "description"):
            value = getattr(scenario, field_name, None)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{field_name} must not be empty.")

        world_state = getattr(scenario, "initial_world_state", None)
        if not isinstance(world_state, Mapping) or not world_state:
            errors.append("initial_world_state must be a non-empty mapping.")

        runtime_config = getattr(scenario, "runtime_config", {})
        if isinstance(runtime_config, Mapping) and "evolution_rules" in runtime_config:
            known_targets = _known_rule_targets(runtime_config, getattr(scenario, "character_templates", ()))
            errors.extend(validate_rule_collection(runtime_config["evolution_rules"], known_targets))
        if isinstance(runtime_config, Mapping) and "cognitive_rules" in runtime_config:
            errors.extend(CognitiveRuleProvider.validate(runtime_config["cognitive_rules"]))

        templates = getattr(scenario, "character_templates", None)
        if not isinstance(templates, (tuple, list)):
            errors.append("character_templates must be a sequence.")
            templates = ()

        character_ids: list[str] = []
        valid_templates: list[Mapping[str, Any]] = []
        for index, template in enumerate(templates):
            if not isinstance(template, Mapping):
                errors.append(f"character_templates[{index}] must be a mapping.")
                continue
            valid_templates.append(template)
            character_id = self._character_id(template)
            if not character_id:
                errors.append(f"character_templates[{index}] must contain a non-empty id.")
            else:
                character_ids.append(character_id)
            self._validate_goals(template, index, errors)

        duplicates = sorted({item for item in character_ids if character_ids.count(item) > 1})
        for duplicate in duplicates:
            errors.append(f"duplicate character id: {duplicate}")

        known_ids = set(character_ids)
        relationships = self._relationship_templates(valid_templates, world_state)
        for index, relationship in enumerate(relationships):
            if not isinstance(relationship, Mapping):
                errors.append(f"relationship_templates[{index}] must be a mapping.")
                continue
            source = self._first_nonempty(relationship, "from", "from_id", "from_character_id")
            target = self._first_nonempty(relationship, "to", "to_id", "to_character_id")
            if not source or not target:
                errors.append(f"relationship_templates[{index}] must define from and to character ids.")
                continue
            if source not in known_ids:
                errors.append(f"relationship_templates[{index}] references unknown source: {source}")
            if target not in known_ids:
                errors.append(f"relationship_templates[{index}] references unknown target: {target}")

        return ValidationResult(valid=not errors, errors=tuple(errors), warnings=tuple(warnings))


    @staticmethod
    def _character_id(template: Mapping[str, Any]) -> str | None:
        value = template.get("id", template.get("character_id"))
        return value.strip() if isinstance(value, str) and value.strip() else None

    @staticmethod
    def _first_nonempty(values: Mapping[str, Any], *keys: str) -> str | None:
        for key in keys:
            value = values.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None

    @staticmethod
    def _validate_goals(template: Mapping[str, Any], index: int, errors: list[str]) -> None:
        if "goal" in template:
            goal = template["goal"]
            if isinstance(goal, str):
                if not goal.strip():
                    errors.append(f"character_templates[{index}].goal must not be empty.")
            elif isinstance(goal, Mapping):
                if not any(
                    isinstance(goal.get(key), str) and goal[key].strip()
                    for key in ("goal_id", "goal_type", "description")
                ):
                    errors.append(f"character_templates[{index}].goal has an invalid format.")
            else:
                errors.append(f"character_templates[{index}].goal has an invalid format.")

        if "goals" not in template:
            return
        goals = template["goals"]
        if isinstance(goals, str) or not isinstance(goals, Sequence):
            errors.append(f"character_templates[{index}].goals must be a sequence.")
            return
        for goal_index, goal in enumerate(goals):
            if isinstance(goal, str) and goal.strip():
                continue
            if isinstance(goal, Mapping) and any(
                isinstance(goal.get(key), str) and goal[key].strip()
                for key in ("goal_id", "goal_type", "description")
            ):
                continue
            errors.append(f"character_templates[{index}].goals[{goal_index}] has an invalid format.")

    @staticmethod
    def _relationship_templates(
        templates: list[Mapping[str, Any]], world_state: Any
    ) -> tuple[Any, ...]:
        relationships: list[Any] = []
        for template in templates:
            raw = template.get("relationships", ())
            if isinstance(raw, (tuple, list)):
                relationships.extend(raw)
            elif raw:
                relationships.append(raw)
        if isinstance(world_state, Mapping):
            raw_world_relationships = world_state.get("relationships", ())
            if isinstance(raw_world_relationships, (tuple, list)):
                relationships.extend(raw_world_relationships)
            elif raw_world_relationships:
                relationships.append(raw_world_relationships)
        return tuple(relationships)
def _known_rule_targets(config, templates):
    targets = {"entity": set(), "location": set(), "item": set(), "resource": set(), "goal": set()}
    for item in config.get("locations", ()):
        if isinstance(item, Mapping) and isinstance(item.get("location_id"), str):
            targets["location"].add(item["location_id"])
    for item in config.get("entities", ()):
        if isinstance(item, Mapping):
            identity = item.get("entity_id", item.get("id"))
            if isinstance(identity, str):
                targets["entity"].add(identity)
    for item in config.get("items", ()):
        if isinstance(item, Mapping):
            identity = item.get("item_id", item.get("id"))
            if isinstance(identity, str):
                targets["item"].add(identity)
    for item in config.get("resources", ()):
        if isinstance(item, Mapping):
            for key in ("resource_id", "resource_type", "id"):
                if isinstance(item.get(key), str):
                    targets["resource"].add(item[key])
    for template in templates if isinstance(templates, (tuple, list)) else ():
        if not isinstance(template, Mapping):
            continue
        character_id = template.get("id", template.get("character_id"))
        if isinstance(character_id, str):
            targets["entity"].add(character_id)
        goals = template.get("goals", ())
        if isinstance(goals, (tuple, list)):
            for goal in goals:
                if isinstance(goal, Mapping):
                    for key in ("goal_id", "goal_type"):
                        if isinstance(goal.get(key), str):
                            targets["goal"].add(goal[key])
                elif isinstance(goal, str):
                    targets["goal"].add(goal)
        goal = template.get("goal")
        if isinstance(goal, Mapping):
            for key in ("goal_id", "goal_type"):
                if isinstance(goal.get(key), str):
                    targets["goal"].add(goal[key])
    for raw in (*config.get("goal_defaults", ()), *config.get("autonomous_goals", ())):
        if isinstance(raw, Mapping):
            for key in ("goal_id", "goal_type"):
                if isinstance(raw.get(key), str):
                    targets["goal"].add(raw[key])
            for key in ("resource_type", "resource_id"):
                if isinstance(raw.get(key), str):
                    targets["resource"].add(raw[key])
    def collect_resources(value):
        if isinstance(value, Mapping):
            for key, item in value.items():
                if key in {"resource_type", "resource_id"} and isinstance(item, str):
                    targets["resource"].add(item)
                if key in {"goal_type", "goal_id"} and isinstance(item, str):
                    targets["goal"].add(item)
                collect_resources(item)
        elif isinstance(value, (tuple, list)):
            for item in value:
                collect_resources(item)
    collect_resources(config)
    return {key: frozenset(value) for key, value in targets.items()}
