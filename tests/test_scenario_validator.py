from dataclasses import FrozenInstanceError

import pytest

from cognitive_sandbox.application.scenario_loader import ScenarioLoader
from cognitive_sandbox.application.scenario_validator import ScenarioValidator
from cognitive_sandbox.application.world_bootstrap import WorldBootstrap
from cognitive_sandbox.domain.scenario import Scenario
from cognitive_sandbox.domain.validation_result import ValidationResult


def _unsafe_scenario(**changes):
    """Build malformed input without bypassing the validator through __post_init__."""
    base = ScenarioLoader().load("post_apocalypse_city")
    scenario = object.__new__(Scenario)
    for field_name in (
        "scenario_id",
        "name",
        "description",
        "initial_world_state",
        "character_templates",
    ):
        object.__setattr__(scenario, field_name, changes.get(field_name, getattr(base, field_name)))
    return scenario


def _scenario(templates=None, state=None):
    return Scenario(
        "valid",
        "场景",
        "描述",
        {"danger_level": 0.2} if state is None else state,
        tuple(templates or ({"id": "one", "name": "一", "role": "survivor", "goals": ()},)),
    )


def test_builtin_scenario_passes_validation():
    result = ScenarioValidator().validate(ScenarioLoader().load("post_apocalypse_city"))

    assert result == ValidationResult(True, (), ())


def test_empty_base_fields_and_world_state_fail_validation():
    malformed = _unsafe_scenario(
        scenario_id=" ",
        name="",
        description="",
        initial_world_state={},
    )

    result = ScenarioValidator().validate(malformed)

    assert not result.valid
    assert any("scenario_id" in error for error in result.errors)
    assert any("name" in error for error in result.errors)
    assert any("description" in error for error in result.errors)
    assert any("initial_world_state" in error for error in result.errors)


def test_duplicate_character_ids_fail_validation():
    scenario = _scenario(
        templates=(
            {"id": "same", "name": "一", "role": "doctor"},
            {"character_id": "same", "name": "二", "role": "soldier"},
        )
    )

    result = ScenarioValidator().validate(scenario)

    assert not result.valid
    assert any("duplicate character id: same" in error for error in result.errors)


def test_invalid_goals_and_relationship_references_fail_validation():
    scenario = _scenario(
        templates=(
            {
                "id": "one",
                "name": "一",
                "role": "doctor",
                "goals": ("",),
                "relationships": ({"from": "one", "to": "missing"},),
            },
        )
    )

    result = ScenarioValidator().validate(scenario)

    assert not result.valid
    assert any("goals" in error and "invalid format" in error for error in result.errors)
    assert any("unknown target: missing" in error for error in result.errors)


def test_validator_does_not_mutate_scenario_or_templates():
    scenario = _scenario()
    before_state = dict(scenario.initial_world_state)
    before_templates = scenario.character_templates

    result = ScenarioValidator().validate(scenario)

    assert result.valid
    assert dict(scenario.initial_world_state) == before_state
    assert scenario.character_templates == before_templates
    with pytest.raises(FrozenInstanceError):
        result.valid = False


def test_bootstrap_rejects_invalid_scenario_before_creating_world_state():
    calls = []
    malformed = _unsafe_scenario(character_templates=({"name": "缺少 id", "role": "doctor"},))
    bootstrap = WorldBootstrap(world_id_factory=lambda: calls.append("world") or "world-1")

    with pytest.raises(ValueError, match="scenario validation failed"):
        bootstrap.create(malformed)
    assert calls == []
