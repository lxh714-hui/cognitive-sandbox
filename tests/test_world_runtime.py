import pytest

from cognitive_sandbox.application.world_runtime import (
    WorldRevisionConflict,
    WorldRuleViolation,
    WorldRuntime,
)
from cognitive_sandbox.domain.actions import ActionProposal
from cognitive_sandbox.infrastructure.sqlite_store import SQLiteEventStore


def proposal(
    proposal_id="proposal_001",
    *,
    actor_id="liang_jing",
    action_type="BREAK_OBJECT",
    target_id="cup_001",
    payload=None,
    world_id="world_001",
    branch_id="main",
    base_world_revision=0,
):
    return ActionProposal(
        proposal_id=proposal_id,
        actor_id=actor_id,
        action_type=action_type,
        target_id=target_id,
        payload={} if payload is None else payload,
        branch_id=branch_id,
        world_id=world_id,
        base_world_revision=base_world_revision,
    )


def make_runtime(store, **kwargs):
    return WorldRuntime(
        store,
        world_id=kwargs.pop("world_id", "world_001"),
        branch_id=kwargs.pop("branch_id", "main"),
        breakable_object_ids=kwargs.pop("breakable_object_ids", {"cup_001"}),
        **kwargs,
    )


def test_liang_jing_breaking_cup_is_validated_and_persisted(tmp_path):
    store = SQLiteEventStore(tmp_path / "world.sqlite3")
    runtime = make_runtime(store)

    event = runtime.submit_action(
        proposal(payload={"object_id": "cup_001"})
    )

    assert event.event_type == "BREAK_OBJECT"
    assert event.actor_id == "liang_jing"
    assert event.payload["object_id"] == "cup_001"
    assert event.world_revision == 1
    assert store.list_world_events("world_001") == [event]
    assert runtime.world_revision == 1


@pytest.mark.parametrize(
    "action",
    [
        proposal(action_type="UNKNOWN_ACTION"),
        proposal(target_id=None),
        proposal(target_id="missing_cup"),
        proposal(payload={"object_id": "another_object"}),
        proposal(world_id="other_world"),
        proposal(branch_id="other_branch"),
    ],
)
def test_invalid_action_proposals_do_not_create_events(tmp_path, action):
    store = SQLiteEventStore(tmp_path / "world.sqlite3")
    runtime = make_runtime(store)

    with pytest.raises(WorldRuleViolation):
        runtime.submit_action(action)

    assert store.list_world_events("world_001") == []
    assert runtime.world_revision == 0


def test_stale_revision_and_already_broken_object_are_rejected(tmp_path):
    store = SQLiteEventStore(tmp_path / "world.sqlite3")
    runtime = make_runtime(store)
    runtime.submit_action(proposal())

    with pytest.raises(WorldRevisionConflict):
        runtime.submit_action(proposal("stale", base_world_revision=0))
    with pytest.raises(WorldRuleViolation):
        runtime.submit_action(proposal("already_broken", base_world_revision=1))

    assert len(store.list_world_events("world_001")) == 1


def test_runtime_restores_revision_and_broken_objects_from_persisted_events(tmp_path):
    store = SQLiteEventStore(tmp_path / "world.sqlite3")
    make_runtime(store).submit_action(proposal())

    restored_runtime = make_runtime(store)
    assert restored_runtime.world_revision == 1
    with pytest.raises(WorldRuleViolation):
        restored_runtime.submit_action(proposal("again", base_world_revision=1))


def test_failed_persistence_does_not_advance_runtime_state():
    class FailingStore:
        def list_world_events(self, world_id):
            return []

        def append_world_event(self, event):
            raise RuntimeError("database unavailable")

    runtime = make_runtime(FailingStore())
    with pytest.raises(RuntimeError, match="database unavailable"):
        runtime.submit_action(proposal())

    assert runtime.world_revision == 0
