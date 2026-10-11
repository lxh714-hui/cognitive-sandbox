import pytest

from cognitive_sandbox.application.cognitive_runtime import CognitiveRuntime
from cognitive_sandbox.application.decision_runtime import DecisionRuntime
from cognitive_sandbox.application.observation_layer import ObservationLayer
from cognitive_sandbox.application.world_runtime import WorldRevisionConflict, WorldRuleViolation, WorldRuntime
from cognitive_sandbox.domain.actions import ActionProposal
from cognitive_sandbox.infrastructure.sqlite_store import SQLiteEventStore


def inspect_proposal(
    *, proposal_id=None, object_id="cup_001", revision=0, target_id="cup_001"
):
    return ActionProposal(
        proposal_id=proposal_id or f"inspect-{object_id}-{revision}",
        actor_id="lin-xia",
        action_type="INSPECT_OBJECT",
        target_id=target_id,
        payload={"object_id": object_id, "private_description": "must not be copied"},
        branch_id="main",
        world_id="harbor",
        base_world_revision=revision,
    )


def make_runtime(store, object_ids=("cup_001",)):
    return WorldRuntime(
        store,
        world_id="harbor",
        branch_id="main",
        breakable_object_ids=object_ids,
    )


def test_inspect_object_creates_minimal_persisted_event(tmp_path):
    store = SQLiteEventStore(tmp_path / "actions.sqlite3")
    runtime = make_runtime(store)

    event = runtime.submit_action(inspect_proposal())

    assert event.event_type == "OBJECT_INSPECTED"
    assert event.payload == {"object_id": "cup_001", "inspector": "lin-xia"}
    assert store.list_world_events("harbor") == [event]


def test_inspect_object_increments_world_revision(tmp_path):
    store = SQLiteEventStore(tmp_path / "actions.sqlite3")
    runtime = make_runtime(store)

    event = runtime.submit_action(inspect_proposal())

    assert event.world_revision == 1
    assert runtime.world_revision == 1


def test_inspect_object_rejects_unknown_or_mismatched_object(tmp_path):
    store = SQLiteEventStore(tmp_path / "actions.sqlite3")
    runtime = make_runtime(store)

    with pytest.raises(WorldRuleViolation, match="does not exist"):
        runtime.submit_action(inspect_proposal(object_id="unknown_cup", target_id="unknown_cup"))
    with pytest.raises(WorldRuleViolation, match="must match"):
        runtime.submit_action(inspect_proposal(object_id="cup_001", target_id="another_cup"))
    missing_object_id = ActionProposal(
        proposal_id="inspect-without-object",
        actor_id="lin-xia",
        action_type="INSPECT_OBJECT",
        target_id=None,
        payload={},
        branch_id="main",
        world_id="harbor",
        base_world_revision=0,
    )
    with pytest.raises(WorldRuleViolation, match="payload.object_id"):
        runtime.submit_action(missing_object_id)

    assert store.list_world_events("harbor") == []
    assert runtime.world_revision == 0


def test_inspect_object_rejects_stale_revision(tmp_path):
    store = SQLiteEventStore(tmp_path / "actions.sqlite3")
    runtime = make_runtime(store)
    runtime.submit_action(inspect_proposal())

    with pytest.raises(WorldRevisionConflict):
        runtime.submit_action(inspect_proposal(revision=0, proposal_id="stale"))

    assert len(store.list_world_events("harbor")) == 1
    assert runtime.world_revision == 1


def test_break_observe_decide_inspect_flow(tmp_path):
    store = SQLiteEventStore(tmp_path / "actions.sqlite3")
    runtime = make_runtime(store)
    broken_event = runtime.submit_action(
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
        broken_event.event_id,
        observer_locations={"lin-xia": "kitchen"},
    )
    observation = observation_layer.produce(task)
    cognition = CognitiveRuntime(store)
    cognition.process_observation(observation)
    [proposal] = DecisionRuntime(cognition).generate_actions("lin-xia")

    inspected_event = runtime.submit_action(proposal)
    events = store.list_world_events("harbor")

    assert [event.event_type for event in events] == ["BREAK_OBJECT", "OBJECT_INSPECTED"]
    assert inspected_event.payload == {"object_id": "cup_001", "inspector": "lin-xia"}
    assert inspected_event.world_revision == 2
    assert "private_description" not in inspected_event.payload
