from dataclasses import FrozenInstanceError

import pytest

from cognitive_sandbox.application.action_decision import ActionDecisionEngine
from cognitive_sandbox.application.action_event_adapter import ActionEventAdapter
from cognitive_sandbox.application.action_resolver import ActionResolver
from cognitive_sandbox.application.agent_context_builder import AgentContextBuilder
from cognitive_sandbox.application.agent_state_updater import AgentStateUpdater
from cognitive_sandbox.application.memory_updater import MemoryUpdater
from cognitive_sandbox.application.multi_agent_simulator import MultiAgentSimulator
from cognitive_sandbox.application.interaction_manager import InteractionManager
from cognitive_sandbox.application.interaction_resolver import InteractionResolver
from cognitive_sandbox.application.relationship_updater import RelationshipUpdater
from cognitive_sandbox.application.simulation_tick import SimulationTick
from cognitive_sandbox.application.world_state_applier import WorldStateApplier
from cognitive_sandbox.application.world_state_updater import WorldStateUpdater
from cognitive_sandbox.domain.agent_context import AgentContext
from cognitive_sandbox.domain.agent_state import AgentDynamicState
from cognitive_sandbox.domain.character import CharacterState
from cognitive_sandbox.domain.memory import InitialMemory
from cognitive_sandbox.domain.relationship import RelationshipState
from cognitive_sandbox.domain.actions import ActionCandidate


def _context(character_id, name, role, relation):
    character = CharacterState(character_id, name, role, (), (), (), ())
    relationships = (RelationshipState(character_id, "other", relation, 0.5),)
    return AgentContext(
        character_id,
        character,
        (InitialMemory(f"memory-{character_id}", "既有经历", 0.4),),
        relationships,
        {"social_trust": 0.5, "danger_level": 0.5},
        AgentDynamicState(character_id, 0.5, 0.1, 0.5),
    )


def _tick(decision_engine=None):
    event_ids = iter(("event-doctor", "event-soldier"))
    action_ids = iter(("action-doctor", "action-doctor-observe", "action-soldier", "action-soldier-observe"))
    memory_ids = iter(("new-memory-doctor", "new-memory-soldier"))
    return SimulationTick(
        decision_engine or ActionDecisionEngine(
            action_id_factory=action_ids.__next__,
            action_rules=(
                {"role_aliases": ("医生",), "situation_aliases": ("受伤",),
                 "intent": "help", "motivation": "care"},
                {"role_aliases": ("士兵",), "situation_aliases": ("危险",),
                 "intent": "protect", "motivation": "duty"},
            ),
        ),
        ActionResolver(),
        ActionEventAdapter(
            world_id="world-1",
            branch_id="main",
            world_revision=1,
            event_id_factory=event_ids.__next__,
        ),
        WorldStateUpdater(),
        WorldStateApplier(),
        MemoryUpdater(memory_id_factory=memory_ids.__next__),
        RelationshipUpdater(),
        AgentStateUpdater(),
        AgentContextBuilder(),
    )


@pytest.fixture
def agents():
    return (
        _context("doctor-1", "林夏", "医生", "care"),
        _context("soldier-1", "梁景", "士兵", "comrade"),
    )


def test_two_agents_run_sequentially_and_preserve_input_order(agents):
    result = MultiAgentSimulator(_tick()).run(
        agents,
        {"social_trust": 0.5, "danger_level": 0.5},
        "危险中发现受伤的病人，需要救助",
    )

    assert tuple(context.character_id for context in result.agent_contexts) == (
        "doctor-1",
        "soldier-1",
    )
    assert tuple(event.actor_id for event in result.events) == ("doctor-1", "soldier-1")


def test_both_agents_generate_events_and_events_are_merged(agents):
    result = MultiAgentSimulator(_tick()).run(
        agents,
        {"social_trust": 0.5, "danger_level": 0.5},
        "危险中发现受伤的病人，需要救助",
    )

    assert len(result.events) == 2
    assert tuple(event.event_type for event in result.events) == (
        "help_attempt",
        "protect_attempt",
    )


def test_world_state_changes_accumulate_between_agents(agents):
    result = MultiAgentSimulator(_tick()).run(
        agents,
        {"social_trust": 0.5, "danger_level": 0.5},
        "危险中发现受伤的病人，需要救助",
    )

    assert result.world_state["social_trust"] == pytest.approx(0.6)
    assert result.world_state["danger_level"] == pytest.approx(0.4)


def test_each_agent_context_is_updated_independently(agents):
    result = MultiAgentSimulator(_tick()).run(
        agents,
        {"social_trust": 0.5, "danger_level": 0.5},
        "危险中发现受伤的病人，需要救助",
    )

    doctor, soldier = result.agent_contexts
    assert len(doctor.memories) == len(agents[0].memories) + 1
    assert doctor.relationships[0].trust == pytest.approx(0.6)
    assert doctor.dynamic_state.confidence == pytest.approx(0.55)
    assert soldier.relationships[0].trust == pytest.approx(0.55)
    assert soldier.dynamic_state.confidence == pytest.approx(0.6)
    assert soldier.dynamic_state.stress == pytest.approx(0.15)


def test_inputs_are_not_modified(agents):
    world_state = {"social_trust": 0.5, "danger_level": 0.5, "nested": {"items": ["cup"]}}
    original_contexts = tuple(agents)

    MultiAgentSimulator(_tick()).run(
        agents,
        world_state,
        "危险中发现受伤的病人，需要救助",
    )

    assert agents == original_contexts
    assert world_state == {
        "social_trust": 0.5,
        "danger_level": 0.5,
        "nested": {"items": ["cup"]},
    }


def test_no_action_preserves_that_agents_original_context(agents):
    class NoActionTick:
        def run(self, context, world_state, situation):
            from cognitive_sandbox.domain.simulation_result import SimulationTickResult

            return SimulationTickResult(world_state, context, ())

    result = MultiAgentSimulator(NoActionTick()).run(agents, {"social_trust": 0.5}, "平静")

    assert result.agent_contexts == agents
    assert result.events == ()
    assert result.world_state == {"social_trust": 0.5}


def test_result_sequences_and_state_are_immutable(agents):
    result = MultiAgentSimulator(_tick()).run(
        agents,
        {"nested": {"items": ["cup"]}, "social_trust": 0.5, "danger_level": 0.5},
        "危险中发现受伤的病人，需要救助",
    )

    assert isinstance(result.agent_contexts, tuple)
    assert isinstance(result.events, tuple)
    with pytest.raises(FrozenInstanceError):
        result.agent_contexts = ()
    with pytest.raises(TypeError):
        result.world_state["nested"]["items"][0] = "book"


def test_simulation_result_includes_interactions_from_selected_action_metadata(agents):
    class TargetingDecisionEngine:
        def generate(self, decision_input):
            actor_id = decision_input.agent_context.character_id
            if actor_id == "doctor-1":
                intent, target_id = "help", "soldier-1"
            else:
                intent, target_id = "protect", "doctor-1"
            return (
                ActionCandidate(
                    action_id=f"action-{actor_id}",
                    actor_id=actor_id,
                    intent=intent,
                    motivation="test",
                    metadata={"target_agent_id": target_id},
                ),
            )

    tick = _tick(TargetingDecisionEngine())
    result = MultiAgentSimulator(tick, InteractionManager(InteractionResolver())).run(
        agents,
        {"social_trust": 0.5, "danger_level": 0.5},
        "危险中发现受伤的病人，需要救助",
    )

    assert tuple(interaction.interaction_type for interaction in result.interactions) == (
        "help_other",
        "protect_other",
    )
    assert tuple(interaction.target_agent_id for interaction in result.interactions) == (
        "soldier-1",
        "doctor-1",
    )
