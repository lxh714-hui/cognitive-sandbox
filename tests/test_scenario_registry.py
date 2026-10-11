import pytest

from cognitive_sandbox.application.scenario_loader import ScenarioLoader
from cognitive_sandbox.application.scenario_registry import ScenarioRegistry
from cognitive_sandbox.domain.scenario import Scenario


def _scenario(scenario_id="s1"):
    return Scenario(scenario_id, "Name", "Description", {"seed": 1}, ())


def test_registry_registers_and_retrieves_same_immutable_scenario():
    registry = ScenarioRegistry()
    scenario = _scenario()

    registry.register(scenario)

    assert registry.get("s1") is scenario
    assert scenario.name == "Name"
    with pytest.raises(ValueError, match="already registered"):
        registry.register(scenario)


def test_registry_lists_available_scenarios_in_registration_order():
    registry = ScenarioRegistry()
    first, second = _scenario("first"), _scenario("second")
    registry.register(first)
    registry.register(second)

    assert registry.list_available() == (first, second)


def test_loader_uses_registry_and_registers_builtin_scenario():
    loader = ScenarioLoader()

    assert loader.registry.get("post_apocalypse_city") is loader.load("post_apocalypse_city")
    assert loader.load("missing") is None
