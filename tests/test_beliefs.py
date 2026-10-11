from dataclasses import FrozenInstanceError, replace

import pytest

from cognitive_sandbox.application.cognitive_runtime import CognitiveRuntime, CognitiveUpdateRejected
from cognitive_sandbox.application.observation_layer import ObservationLayer
from cognitive_sandbox.application.world_runtime import WorldRuntime
from cognitive_sandbox.domain.actions import ActionProposal
from cognitive_sandbox.domain.cognition import Belief
from cognitive_sandbox.infrastructure.sqlite_store import SQLiteEventStore


def _observation(store, *, observer_id="lin-xia"):
    world = WorldRuntime(
        store,
        world_id="harbor",
        branch_id="main",
        breakable_object_ids={"cup_001"},
        event_id_factory=lambda: "event-break-cup",
    )
    event = world.submit_action(
        ActionProposal(
            proposal_id="proposal-break-cup",
            actor_id="liang-jing",
            action_type="BREAK_OBJECT",
            target_id="cup_001",
            payload={"location_id": "kitchen"},
            branch_id="main",
            world_id="harbor",
            base_world_revision=0,
        )
    )
    layer = ObservationLayer(
        store,
        id_factory=lambda: "observation-break-cup",
        clock=lambda: "2026-10-11T12:00:00+00:00",
    )
    [task] = layer.create_tasks(event.event_id, observer_locations={observer_id: "kitchen"})
    return layer.produce(task)


def test_belief_model_is_immutable_and_validates_confidence_and_sources():
    belief = Belief(
        belief_id="belief-1",
        agent_id="lin-xia",
        belief_type="perceptual",
        proposition="The cup broke.",
        confidence=0.8,
        source_refs=("observation-1",),
    )

    with pytest.raises(FrozenInstanceError):
        belief.confidence = 0.1
    with pytest.raises(ValueError, match="between 0 and 1"):
        replace(belief, confidence=1.1)
    with pytest.raises(ValueError, match="source_refs"):
        replace(belief, source_refs=())


def test_cognitive_runtime_generates_and_persists_observation_sourced_belief(tmp_path):
    database_path = tmp_path / "beliefs.sqlite3"
    store = SQLiteEventStore(database_path)
    observation = replace(_observation(store), uncertainty=0.25)
    runtime = CognitiveRuntime(store)

    state = runtime.process_observation(observation)
    [stored] = store.list_beliefs_for_agent("lin-xia")
    [history] = store.list_cognitive_change_history("lin-xia")

    assert len(state.beliefs) == 1
    belief = state.beliefs[0]
    assert belief.belief_type == "perceptual"
    assert belief.proposition == observation.content
    assert belief.confidence == pytest.approx(0.75)
    assert belief.source_refs == (observation.observation_id,)
    assert observation.source_refs[0] not in belief.source_refs
    assert stored == belief
    assert history["state"].beliefs == (belief,)

    restarted = CognitiveRuntime(SQLiteEventStore(database_path))
    assert restarted.get_state("lin-xia").beliefs == (belief,)


def test_beliefs_are_agent_scoped_and_same_observation_is_not_duplicated(tmp_path):
    store = SQLiteEventStore(tmp_path / "beliefs.sqlite3")
    observation = _observation(store)
    runtime = CognitiveRuntime(store)

    first_state = runtime.process_observation(observation)
    second_state = runtime.process_observation(observation)

    assert len(first_state.beliefs) == 1
    assert second_state.beliefs == first_state.beliefs
    assert store.list_beliefs_for_agent("lin-xia") == list(first_state.beliefs)
    assert store.list_beliefs_for_agent("another-agent") == []
    assert runtime.get_state("another-agent").beliefs == ()


def test_uncommitted_observation_cannot_create_a_belief(tmp_path):
    store = SQLiteEventStore(tmp_path / "beliefs.sqlite3")
    runtime = CognitiveRuntime(store)
    from cognitive_sandbox.domain.observations import ObservationRecord

    observation = ObservationRecord(
        observation_id="untrusted-observation",
        agent_id="lin-xia",
        source_refs=("missing-world-event",),
        observed_at="2026-10-11T12:00:00+00:00",
        channel="visual",
        content="A cup broke.",
        uncertainty=0.1,
    )

    with pytest.raises(CognitiveUpdateRejected, match="not committed"):
        runtime.process_observation(observation)
    assert store.list_beliefs_for_agent("lin-xia") == []
