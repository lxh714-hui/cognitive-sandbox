from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from cognitive_sandbox.application.scenario_runtime_builder import ScenarioRuntimeBuilder
from cognitive_sandbox.application.world_bootstrap import WorldBootstrap
from cognitive_sandbox.domain.agent_context import AgentContext
from cognitive_sandbox.domain.character_card import CharacterCard
from cognitive_sandbox.domain.constraint import Constraint
from cognitive_sandbox.domain.event_card import EventCard
from cognitive_sandbox.domain.scenario import Scenario
from cognitive_sandbox.domain.scenario_content import ScenarioContent
from cognitive_sandbox.domain.scenario_runtime import AgentRuntimeProfile, ScenarioRuntime
from cognitive_sandbox.domain.world_document import WorldDocument
from cognitive_sandbox.domain.world_state import WorldState


def _content():
    scenario = Scenario(
        "post_apocalypse_city",
        "末日城市开局",
        "城市医院正值深夜。",
        {"danger_level": 0.5, "resource_level": 0.3},
        (),
    )
    world_document = WorldDocument(
        "harbor_city",
        "末日城市",
        "灾难后的城市",
        ("三年前灾难爆发",),
        ("感染不可逆",),
    )
    doctor = CharacterCard(
        "doctor",
        "林夏",
        age=29,
        gender="女",
        occupation="医生",
        personality=("compassionate", "谨慎"),
        goals=("help others",),
        constraints=(Constraint("hard", "不会伤害无辜者"),),
    )
    soldier = CharacterCard(
        "soldier",
        "梁景",
        occupation="士兵",
        personality=("brave",),
        goals=("protect others",),
    )
    event = EventCard(
        "hospital_power_failure",
        "医院停电",
        "医院备用电源即将耗尽",
        "initial",
        ("doctor", "soldier"),
        ("night",),
        ("hospital_dark",),
        1,
    )
    return ScenarioContent(scenario, world_document, [doctor, soldier], [event])


def test_scenario_content_builds_world_agents_and_unexecuted_initial_events():
    content = _content()

    runtime = ScenarioRuntimeBuilder().build(content)

    assert isinstance(runtime, ScenarioRuntime)
    assert isinstance(runtime.world_state, WorldState)
    assert runtime.scenario_id == "post_apocalypse_city"
    assert runtime.world_state.world_id == "harbor_city"
    assert runtime.world_state.name == "末日城市"
    assert runtime.world_state.description == "灾难后的城市"
    assert runtime.world_state.history == ("三年前灾难爆发",)
    assert runtime.world_state.rules == ("感染不可逆",)
    assert runtime.world_state.state == {"danger_level": 0.5, "resource_level": 0.3}
    assert runtime.initial_events == content.event_cards
    assert len(runtime.agent_contexts) == 2


def test_character_cards_map_to_agent_contexts_and_keep_constraints_separate():
    runtime = ScenarioRuntimeBuilder().build(_content())

    assert all(isinstance(context, AgentContext) for context in runtime.agent_contexts)
    doctor, soldier = runtime.agents
    assert isinstance(doctor, AgentRuntimeProfile)
    assert doctor.agent_context.character_id == "doctor"
    assert doctor.agent_context.character_state.name == "林夏"
    assert doctor.agent_context.character_state.role == "医生"
    assert doctor.agent_context.character_state.traits == ("compassionate", "谨慎")
    assert doctor.agent_context.character_state.goals == ("help others",)
    assert doctor.constraints == (Constraint("hard", "不会伤害无辜者"),)
    assert soldier.agent_context.character_id == "soldier"
    assert soldier.agent_context.character_state.traits == ("brave",)
    assert soldier.constraints == ()


def test_world_bootstrap_delegates_content_runtime_building_and_keeps_legacy_flow():
    content = _content()
    bootstrap = WorldBootstrap(world_id_factory=lambda: "legacy-world")

    runtime = bootstrap.create_from_content(content)
    legacy = bootstrap.create(content.scenario)

    assert runtime.world_state.world_id == "harbor_city"
    assert legacy.world_state.world_id == "legacy-world"
    assert legacy.world_state.description == content.scenario.description


def test_validation_failure_prevents_any_world_runtime_creation():
    class SpyBootstrap(WorldBootstrap):
        calls = 0

        def create_world_from_document(self, document, initial_state):
            self.calls += 1
            return super().create_world_from_document(document, initial_state)

    content = _content()
    invalid_event = object.__new__(EventCard)
    object.__setattr__(invalid_event, "event_id", "")
    object.__setattr__(invalid_event, "name", "broken")
    object.__setattr__(invalid_event, "description", "bad event")
    object.__setattr__(invalid_event, "event_type", "initial")
    object.__setattr__(invalid_event, "participants", ())
    object.__setattr__(invalid_event, "conditions", ())
    object.__setattr__(invalid_event, "effects", ())
    object.__setattr__(invalid_event, "priority", 0)
    invalid_content = ScenarioContent(
        content.scenario,
        content.world_document,
        content.character_cards,
        (invalid_event,),
    )
    bootstrap = SpyBootstrap()

    with pytest.raises(ValueError, match="scenario content validation failed"):
        ScenarioRuntimeBuilder(world_bootstrap=bootstrap).build(invalid_content)

    assert bootstrap.calls == 0


def test_build_keeps_input_immutable_and_runtime_results_are_immutable():
    source = _content()
    original = (
        dict(source.scenario.initial_world_state),
        source.character_cards,
        source.event_cards,
        source.world_document.history,
    )

    runtime = ScenarioRuntimeBuilder().build(source)

    assert dict(source.scenario.initial_world_state) == original[0]
    assert source.character_cards == original[1]
    assert source.event_cards == original[2]
    assert source.world_document.history == original[3]
    with pytest.raises(FrozenInstanceError):
        runtime.initial_events = ()
    with pytest.raises(TypeError):
        runtime.world_state.state["danger_level"] = 1.0
    with pytest.raises(TypeError):
        runtime.agent_contexts[0].world_state["danger_level"] = 1.0
