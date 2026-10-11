import pytest

from cognitive_sandbox.application.action_resolver import ActionResolver
from cognitive_sandbox.application.world_runtime import (
    WorldRevisionConflict,
    WorldRuleViolation,
    WorldRuntime,
)
from cognitive_sandbox.domain.actions import ActionProposal, ResolvedAction
from cognitive_sandbox.infrastructure.sqlite_store import SQLiteEventStore


def _proposal(
    proposal_id="proposal-1",
    *,
    action_type="BREAK_OBJECT",
    target_id="cup_001",
    revision=0,
    world_id="harbor",
):
    return ActionProposal(
        proposal_id=proposal_id,
        actor_id="lin-xia",
        action_type=action_type,
        target_id=target_id,
        payload={},
        branch_id="main",
        world_id=world_id,
        base_world_revision=revision,
    )


def _runtime(store):
    return WorldRuntime(
        store,
        world_id="harbor",
        branch_id="main",
        breakable_object_ids={"cup_001"},
    )


def test_accepted_resolved_action_executes_and_persists_world_event(tmp_path):
    store = SQLiteEventStore(tmp_path / "resolved-action.sqlite3")
    runtime = _runtime(store)
    [resolved] = ActionResolver().resolve([_proposal()], current_world_revision=0)

    event = runtime.execute_action(resolved)

    assert event is not None
    assert event.event_type == "BREAK_OBJECT"
    assert event.actor_id == "lin-xia"
    assert event.payload["object_id"] == "cup_001"
    assert event.world_revision == 1
    assert store.list_world_events("harbor") == [event]
    assert runtime.world_revision == 1


def test_rejected_resolved_action_returns_none_without_world_changes(tmp_path):
    store = SQLiteEventStore(tmp_path / "rejected-action.sqlite3")
    runtime = _runtime(store)
    rejected = ResolvedAction(_proposal(), False, "Lower priority.")

    assert runtime.execute_action(rejected) is None
    assert store.list_world_events("harbor") == []
    assert runtime.world_revision == 0


def test_accepted_action_is_revalidated_for_revision_and_world_rules(tmp_path):
    store = SQLiteEventStore(tmp_path / "revalidated-action.sqlite3")
    runtime = _runtime(store)
    [accepted] = ActionResolver().resolve([_proposal()], current_world_revision=0)
    runtime.execute_action(accepted)

    stale = ResolvedAction(_proposal("stale", revision=0), True, "Previously accepted.")
    with pytest.raises(WorldRevisionConflict):
        runtime.execute_action(stale)
    unavailable = ResolvedAction(
        _proposal("already-broken", revision=1), True, "Previously accepted."
    )
    with pytest.raises(WorldRuleViolation, match="not available"):
        runtime.execute_action(unavailable)

    assert len(store.list_world_events("harbor")) == 1
    assert runtime.world_revision == 1


def test_accepted_action_with_wrong_world_is_rejected_by_world_runtime(tmp_path):
    store = SQLiteEventStore(tmp_path / "wrong-world-action.sqlite3")
    runtime = _runtime(store)
    wrong_world = ResolvedAction(
        _proposal(world_id="elsewhere"), True, "Previously accepted."
    )

    with pytest.raises(WorldRuleViolation, match="world or branch"):
        runtime.execute_action(wrong_world)
    assert store.list_world_events("harbor") == []
    assert runtime.world_revision == 0


def test_execute_action_requires_resolved_action(tmp_path):
    runtime = _runtime(SQLiteEventStore(tmp_path / "wrong-type.sqlite3"))

    with pytest.raises(TypeError, match="ResolvedAction"):
        runtime.execute_action(_proposal())
