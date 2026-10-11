from dataclasses import FrozenInstanceError

import pytest

from cognitive_sandbox.application.scenario_loader import ScenarioLoader
from cognitive_sandbox.domain.scenario import Scenario


def test_loader_returns_built_in_post_apocalypse_scenario():
    scenario = ScenarioLoader().load("post_apocalypse_city")

    assert isinstance(scenario, Scenario)
    assert scenario.name == "末日城市"
    assert scenario.initial_world_state["danger_level"] == 0.5
    assert scenario.initial_world_state["resource_level"] == 0.3
    assert isinstance(scenario.character_templates, tuple)
    assert len(scenario.character_templates) == 3


def test_loader_returns_none_for_unknown_scenario():
    assert ScenarioLoader().load("unknown") is None


def test_scenario_freezes_nested_world_state_and_character_templates():
    world_state = {"nested": {"tags": ["quiet"]}}
    template = {"character_id": "one", "traits": ["adaptive"]}
    scenario = Scenario("s", "name", "description", world_state, [template])
    world_state["nested"]["tags"].append("changed")
    template["traits"].append("changed")

    assert scenario.initial_world_state["nested"]["tags"] == ("quiet",)
    assert scenario.character_templates[0]["traits"] == ("adaptive",)
    with pytest.raises(TypeError):
        scenario.initial_world_state["nested"]["new"] = True
    with pytest.raises(FrozenInstanceError):
        scenario.name = "changed"
