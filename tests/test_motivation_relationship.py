from dataclasses import FrozenInstanceError

import pytest

from cognitive_sandbox.application.cognitive_runtime import CognitiveRuntime
from cognitive_sandbox.application.decision_runtime import DecisionRuntime
from cognitive_sandbox.application.observation_layer import ObservationLayer
from cognitive_sandbox.application.world_runtime import WorldRuntime
from cognitive_sandbox.domain.actions import ActionProposal
from cognitive_sandbox.domain.cognition import Goal, Relationship
from cognitive_sandbox.infrastructure.sqlite_store import SQLiteEventStore


def _goal(goal_id="goal-investigate", agent_id="lin-xia", **overrides):
    values = {
        "goal_id": goal_id,
        "agent_id": agent_id,
        "goal_type": "investigate",
        "description": "Find out what happened to the cup.",
        "priority": 0.8,
        "status": "active",
        "source_refs": ("observation-goal",),
    }
    return Goal(**(values | overrides))


def _relationship(relationship_id, from_agent, to_agent, trust):
    return Relationship(
        relationship_id=relationship_id,
        from_agent_id=from_agent,
        to_agent_id=to_agent,
        trust=trust,
        affinity=0.5,
        hostility=0.1,
        source_refs=(f"observation-{relationship_id}",),
    )


def _build_observing_agent(store):
    world = WorldRuntime(
        store,
        world_id="harbor",
        branch_id="main",
        breakable_object_ids={"cup_001"},
    )
    event = world.submit_action(
        ActionProposal(
            proposal_id="break-cup",
            actor_id="liang-jing",
            action_type="BREAK_OBJECT",
            target_id="cup_001",
            payload={"location_id": "kitchen"},
            branch_id="main",
            world_id="harbor",
            base_world_revision=0,
        )
    )
    observations = ObservationLayer(store)
    [task] = observations.create_tasks(
        event.event_id,
        observer_locations={"lin-xia": "kitchen"},
    )
    CognitiveRuntime(store).process_observation(observations.produce(task))


def test_goal_is_immutable_and_validates_priority_and_required_fields():
    goal = _goal()

    assert goal.goal_type == "investigate"
    assert goal.priority == 0.8
    with pytest.raises(FrozenInstanceError):
        goal.status = "completed"
    with pytest.raises(ValueError, match="between 0 and 1"):
        _goal(priority=1.1)
    with pytest.raises(ValueError, match="agent_id"):
        _goal(agent_id=" ")


def test_relationship_direction_is_independent(tmp_path):
    store = SQLiteEventStore(tmp_path / "motivation.sqlite3")
    a_to_b = _relationship("a-to-b", "agent-a", "agent-b", 0.9)
    b_to_a = _relationship("b-to-a", "agent-b", "agent-a", 0.2)
    store.append_relationship(a_to_b)
    store.append_relationship(b_to_a)

    assert store.list_relationships_for_agent("agent-a") == [a_to_b]
    assert store.list_relationships_for_agent("agent-b") == [b_to_a]


def test_goal_persists_and_is_scoped_to_its_agent(tmp_path):
    store = SQLiteEventStore(tmp_path / "motivation.sqlite3")
    goal = _goal()

    store.append_goal(goal)

    assert store.list_goals_for_agent("lin-xia") == [goal]
    assert store.list_goals_for_agent("liang-jing") == []


def test_active_investigate_goal_drives_inspection_proposal(tmp_path):
    store = SQLiteEventStore(tmp_path / "motivation.sqlite3")
    _build_observing_agent(store)
    store.append_goal(_goal())

    [proposal] = DecisionRuntime(CognitiveRuntime(store), store).generate_actions("lin-xia")

    assert proposal.action_type == "INSPECT_OBJECT"
    assert proposal.target_id == "cup_001"
    assert proposal.payload["decision_rule"] == "investigate_goal_after_observing_damage"
    assert proposal.priority == pytest.approx(0.6035)


def test_no_goal_preserves_existing_emotion_driven_action(tmp_path):
    store = SQLiteEventStore(tmp_path / "motivation.sqlite3")
    _build_observing_agent(store)

    [proposal] = DecisionRuntime(CognitiveRuntime(store), store).generate_actions("lin-xia")

    assert proposal.action_type == "INSPECT_OBJECT"
    assert proposal.payload["decision_rule"] == "inspect_object_after_observing_damage"
    assert proposal.priority == pytest.approx(0.5075)


def test_high_trust_relationship_increases_proposal_priority(tmp_path):
    store = SQLiteEventStore(tmp_path / "motivation.sqlite3")
    _build_observing_agent(store)
    store.append_relationship(_relationship("lin-trusts-liang", "lin-xia", "liang-jing", 0.9))

    [proposal] = DecisionRuntime(CognitiveRuntime(store), store).generate_actions("lin-xia")

    assert proposal.priority == pytest.approx(0.5795)


def test_low_trust_does_not_change_existing_action_priority(tmp_path):
    store = SQLiteEventStore(tmp_path / "motivation.sqlite3")
    _build_observing_agent(store)
    store.append_relationship(_relationship("lin-distrusts-liang", "lin-xia", "liang-jing", 0.2))

    [proposal] = DecisionRuntime(CognitiveRuntime(store), store).generate_actions("lin-xia")

    assert proposal.priority == pytest.approx(0.5075)
