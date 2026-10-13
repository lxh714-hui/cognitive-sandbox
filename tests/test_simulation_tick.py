from dataclasses import FrozenInstanceError

import pytest

from cognitive_sandbox.application.action_decision import ActionDecisionEngine
from cognitive_sandbox.application.action_event_adapter import ActionEventAdapter
from cognitive_sandbox.application.action_resolver import ActionResolver
from cognitive_sandbox.application.agent_context_builder import AgentContextBuilder
from cognitive_sandbox.application.agent_state_updater import AgentStateUpdater
from cognitive_sandbox.application.memory_updater import MemoryUpdater
from cognitive_sandbox.application.relationship_updater import RelationshipUpdater
from cognitive_sandbox.application.simulation_tick import SimulationTick
from cognitive_sandbox.application.world_state_applier import WorldStateApplier
from cognitive_sandbox.application.world_state_updater import WorldStateUpdater
from cognitive_sandbox.domain.agent_context import AgentContext
from cognitive_sandbox.domain.agent_state import AgentDynamicState
from cognitive_sandbox.domain.character import CharacterState
from cognitive_sandbox.domain.memory import InitialMemory
from cognitive_sandbox.domain.relationship import RelationshipState


def make_context():
    character = CharacterState("agent-1", "林夏", "医生", (), (), (), ())
    memories = (InitialMemory("memory-old", "曾经照顾过病人", 0.4),)
    relationships = (RelationshipState("agent-1", "agent-2", "care", 0.5),)
    dynamic = AgentDynamicState("agent-1", 0.5, 0.2, 0.5)
    return AgentContext("agent-1", character, memories, relationships, {"social_trust": 0.5}, dynamic)


def make_tick(engine=None):
    return SimulationTick(
        engine or ActionDecisionEngine(
            action_id_factory=iter(("act-help", "act-observe")).__next__,
            action_rules=({
                "role_aliases": ("医生",), "situation_aliases": ("病人受伤", "病人"),
                "intent": "help", "motivation": "care",
            },),
        ),
        ActionResolver(),
        ActionEventAdapter(
            world_id="world-1",
            branch_id="main",
            world_revision=1,
            event_id_factory=lambda: "event-1",
        ),
        WorldStateUpdater(),
        WorldStateApplier(),
        MemoryUpdater(memory_id_factory=lambda: "memory-new"),
        RelationshipUpdater(),
        AgentStateUpdater(),
        AgentContextBuilder(),
    )


def test_full_tick_updates_world_memory_relationship_and_dynamic_state():
    context = make_context()
    world_state = {"social_trust": 0.5, "nested": {"items": ["cup"]}}

    result = make_tick().run(context, world_state, "病人受伤，需要救助")

    assert result.events[0].event_type == "help_attempt"
    assert result.events[0].actor_id == "agent-1"
    assert result.world_state["social_trust"] == pytest.approx(0.6)
    assert len(result.agent_context.memories) == 2
    assert result.agent_context.memories[-1].content == "我曾经帮助过他人"
    assert result.agent_context.relationships[0].trust == pytest.approx(0.6)
    assert result.agent_context.dynamic_state.confidence == pytest.approx(0.55)
    assert result.agent_context.dynamic_state.motivation == pytest.approx(0.55)
    assert result.agent_context.world_state["social_trust"] == pytest.approx(0.6)
    assert context.world_state["social_trust"] == 0.5
    assert context.memories == (context.memories[0],)
    assert context.relationships[0].trust == 0.5


def test_tick_keeps_event_record_and_refreshes_all_context_fields():
    result = make_tick().run(make_context(), {"information_level": 0.0}, "街道上很安静")

    event = result.events[0]
    assert event.event_type == "observe_action"
    assert result.agent_context.character_state.role == "医生"
    assert result.agent_context.memories[-1].memory_id == "memory-new"
    assert result.agent_context.world_state == result.world_state


def test_observe_tick_changes_world_and_dynamic_state():
    result = make_tick().run(make_context(), {}, "没有值得处理的情况")

    assert result.events[0].event_type == "observe_action"
    assert result.world_state["information_level"] == pytest.approx(0.1)
    assert result.agent_context.dynamic_state.motivation == pytest.approx(0.52)


def test_no_action_candidate_returns_unchanged_state_and_context():
    class NoActions:
        def generate(self, decision_input):
            return ()

    context = make_context()
    state = {"nested": {"items": [1]}}
    result = make_tick(NoActions()).run(context, state, "周围很安静")

    assert result.events == ()
    assert result.agent_context is context
    assert result.world_state == {"nested": {"items": (1,)}}
    assert state == {"nested": {"items": [1]}}


def test_result_is_immutable_and_world_state_is_deeply_read_only():
    result = make_tick().run(make_context(), {"nested": {"items": ["cup"]}}, "街道很安静")

    with pytest.raises(FrozenInstanceError):
        result.events = ()
    with pytest.raises(TypeError):
        result.world_state["nested"]["items"][0] = "book"
    assert isinstance(result.events, tuple)


def test_selected_first_candidate_is_the_only_action_resolved():
    context = make_context()
    result = make_tick().run(context, {}, "病人受伤")
    assert result.events[0].event_type == "help_attempt"

