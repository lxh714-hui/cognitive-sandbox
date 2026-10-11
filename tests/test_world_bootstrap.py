from dataclasses import FrozenInstanceError

import pytest

from cognitive_sandbox.application.scenario_loader import ScenarioLoader
from cognitive_sandbox.application.world_bootstrap import WorldBootstrap
from cognitive_sandbox.domain.agent_context import AgentContext
from cognitive_sandbox.domain.world_state import WorldState


def test_bootstrap_creates_world_state_and_agent_contexts():
    scenario = ScenarioLoader().load("post_apocalypse_city")
    result = WorldBootstrap(world_id_factory=lambda: "world-1").create(scenario)

    assert isinstance(result.world_state, WorldState)
    assert result.world_state.world_id == "world-1"
    assert result.world_state.name == "末日城市"
    assert result.world_state.state == {"danger_level": 0.5, "resource_level": 0.3}
    assert len(result.agent_contexts) == 3
    assert all(isinstance(context, AgentContext) for context in result.agent_contexts)


def test_bootstrap_builds_expected_character_contexts():
    scenario = ScenarioLoader().load("post_apocalypse_city")
    result = WorldBootstrap(world_id_factory=lambda: "world-1").create(scenario)
    contexts = {context.character_id: context for context in result.agent_contexts}

    assert contexts["doctor"].character_state.traits == ("compassionate",)
    assert contexts["doctor"].character_state.goals == ("help others",)
    assert contexts["soldier"].character_state.traits == ("brave",)
    assert contexts["soldier"].character_state.goals == ("protect others",)
    assert contexts["survivor"].character_state.traits == ("adaptive",)
    assert all(context.world_state == result.world_state.state for context in result.agent_contexts)


def test_bootstrap_keeps_source_scenario_data_unchanged_and_outputs_immutable():
    scenario = ScenarioLoader().load("post_apocalypse_city")
    original_state = dict(scenario.initial_world_state)
    original_templates = scenario.character_templates

    result = WorldBootstrap(world_id_factory=lambda: "world-1").create(scenario)

    assert dict(scenario.initial_world_state) == original_state
    assert scenario.character_templates == original_templates
    with pytest.raises(TypeError):
        result.world_state.state["danger_level"] = 1.0
    with pytest.raises(FrozenInstanceError):
        result.agent_contexts = ()
    with pytest.raises(TypeError):
        result.agent_contexts[0].world_state["danger_level"] = 1.0
