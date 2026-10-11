from dataclasses import replace

import pytest

from cognitive_sandbox.application.cognitive_runtime import (
    CognitiveRevisionConflict,
    CognitiveRuntime,
    CognitiveUpdateRejected,
)
from cognitive_sandbox.application.observation_layer import ObservationLayer
from cognitive_sandbox.application.world_runtime import WorldRuntime
from cognitive_sandbox.domain.actions import ActionProposal
from cognitive_sandbox.domain.cognition import CognitiveUpdateProposal, ProposalOperation
from cognitive_sandbox.domain.observations import ObservationRecord
from cognitive_sandbox.infrastructure.sqlite_store import SQLiteEventStore


def make_observation(store, *, observer_id="lin-xia"):
    world_runtime = WorldRuntime(
        store,
        world_id="harbor",
        branch_id="main",
        breakable_object_ids={"cup_001"},
    )
    event = world_runtime.submit_action(
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
    observation_layer = ObservationLayer(store)
    [task] = observation_layer.create_tasks(
        event.event_id,
        observer_locations={observer_id: "kitchen"},
    )
    return observation_layer.produce(task)


def test_observation_commits_working_memory_emotion_and_history(tmp_path):
    store = SQLiteEventStore(tmp_path / "cognitive.sqlite3")
    observation = make_observation(store)
    runtime = CognitiveRuntime(
        store,
        id_factory=iter(("proposal-1", "memory-1")).__next__,
        clock=lambda: "2026-10-11T12:00:00+00:00",
    )

    state = runtime.process_observation(observation)

    assert state.agent_id == "lin-xia"
    assert state.cognitive_revision == 1
    assert len(state.working_memory) == 1
    item = state.working_memory[0]
    assert item.agent_id == "lin-xia"
    assert item.content["text"] == observation.content
    assert item.source_refs == (observation.observation_id,)
    assert item.priority == 1.0
    assert state.emotion_state.valence == pytest.approx(-0.2)
    assert state.emotion_state.arousal == pytest.approx(0.25)
    assert state.emotion_state.source_refs == (observation.observation_id,)

    [restored] = store.list_cognitive_change_history("lin-xia")
    assert restored["state"] == state
    assert restored["source_refs"] == (observation.observation_id,)
    assert runtime.get_state("lin-xia") == state


def test_cognitive_state_is_isolated_per_agent(tmp_path):
    store = SQLiteEventStore(tmp_path / "cognitive.sqlite3")
    observation = make_observation(store, observer_id="lin-xia")
    runtime = CognitiveRuntime(store)

    runtime.process_observation(observation)

    assert runtime.get_state("lin-xia").cognitive_revision == 1
    assert runtime.get_state("another-npc").cognitive_revision == 0
    assert runtime.get_state("another-npc").working_memory == ()


def test_runtime_rejects_observations_without_committed_sources(tmp_path):
    store = SQLiteEventStore(tmp_path / "cognitive.sqlite3")
    runtime = CognitiveRuntime(store)
    forged = ObservationRecord(
        observation_id="untrusted-observation",
        agent_id="lin-xia",
        source_refs=("missing-event",),
        observed_at="2026-10-11T12:00:00+00:00",
        channel="visual",
        content="A cup broke.",
        uncertainty=0,
    )

    with pytest.raises(CognitiveUpdateRejected, match="not committed"):
        runtime.process_observation(forged)
    assert runtime.get_state("lin-xia").cognitive_revision == 0


def test_runtime_rejects_proposals_with_wrong_agent_source_or_operation(tmp_path):
    store = SQLiteEventStore(tmp_path / "cognitive.sqlite3")
    observation = make_observation(store)
    runtime = CognitiveRuntime(store)
    valid_fields = {
        "proposal_id": "manual-proposal",
        "agent_id": "lin-xia",
        "target_layer": CognitiveRuntime.TARGET_LAYER,
        "operation": ProposalOperation.CREATE,
        "source_refs": (observation.observation_id,),
        "reason": "test proposal",
        "base_cognitive_revision": 0,
        "world_revision": 1,
    }

    for overrides, error in (
        ({"agent_id": "another-agent"}, "agent"),
        ({"source_refs": ("another-observation",)}, "cite"),
        ({"operation": ProposalOperation.ACTIVATE}, "operation"),
        ({"target_layer": "long_term_memory"}, "target layer"),
        ({"world_revision": 0}, "world revision"),
    ):
        proposal = CognitiveUpdateProposal(**(valid_fields | overrides))
        with pytest.raises(CognitiveUpdateRejected, match=error):
            runtime.submit_proposal(proposal, observation)

    assert runtime.get_state("lin-xia").cognitive_revision == 0


def test_stale_cognitive_revision_is_rejected(tmp_path):
    store = SQLiteEventStore(tmp_path / "cognitive.sqlite3")
    observation = make_observation(store)
    runtime = CognitiveRuntime(store)
    runtime.process_observation(observation)
    stale = CognitiveUpdateProposal(
        proposal_id="stale-proposal",
        agent_id="lin-xia",
        target_layer=runtime.TARGET_LAYER,
        operation=ProposalOperation.CREATE,
        source_refs=(observation.observation_id,),
        reason="stale update",
        base_cognitive_revision=0,
        world_revision=1,
    )

    with pytest.raises(CognitiveUpdateRejected, match="operation"):
        runtime.submit_proposal(stale, observation)

    stale_update = replace(stale, operation=ProposalOperation.UPDATE)
    with pytest.raises(CognitiveRevisionConflict, match="stale"):
        runtime.submit_proposal(stale_update, observation)
    assert runtime.get_state("lin-xia").cognitive_revision == 1


def test_state_and_history_survive_runtime_restart(tmp_path):
    store = SQLiteEventStore(tmp_path / "cognitive.sqlite3")
    observation = make_observation(store)
    CognitiveRuntime(store).process_observation(observation)

    restarted = CognitiveRuntime(store)
    state = restarted.get_state("lin-xia")
    assert state.cognitive_revision == 1
    assert state.working_memory[0].source_refs == (observation.observation_id,)
    assert len(store.list_cognitive_change_history("lin-xia")) == 1
