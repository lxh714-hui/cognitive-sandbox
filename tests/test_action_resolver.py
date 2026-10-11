from dataclasses import FrozenInstanceError

import pytest

from cognitive_sandbox.application.action_resolver import ActionResolver
from cognitive_sandbox.domain.actions import ActionProposal, ResolvedAction


def _proposal(proposal_id, actor_id, priority, revision=4):
    return ActionProposal(
        proposal_id=proposal_id,
        actor_id=actor_id,
        action_type="INSPECT_OBJECT",
        target_id="cup_001",
        payload={},
        branch_id="main",
        world_id="harbor",
        base_world_revision=revision,
        priority=priority,
    )


def test_resolver_sorts_by_priority_and_applies_stable_tie_breaks():
    proposals = [
        _proposal("z-proposal", "agent-b", 0.8),
        _proposal("b-proposal", "agent-a", 0.8),
        _proposal("a-proposal", "agent-a", 0.8),
        _proposal("low", "agent-c", 0.3),
    ]

    resolved = ActionResolver().resolve(proposals, current_world_revision=4)

    assert [item.action.proposal_id for item in resolved] == [
        "a-proposal",
        "b-proposal",
        "z-proposal",
        "low",
    ]
    assert [item.accepted for item in resolved] == [True, False, True, True]
    assert "higher-priority" in resolved[1].reason


def test_resolver_rejects_stale_or_future_world_revisions():
    proposals = [
        _proposal("stale", "agent-a", 0.9, revision=3),
        _proposal("current", "agent-b", 0.7, revision=4),
        _proposal("future", "agent-c", 0.6, revision=5),
    ]

    resolved = ActionResolver().resolve(proposals, current_world_revision=4)

    assert {item.action.proposal_id: item.accepted for item in resolved} == {
        "stale": False,
        "current": True,
        "future": False,
    }
    assert "revision" in resolved[0].reason
    assert "revision" in resolved[2].reason


def test_resolver_accepts_at_most_one_proposal_per_agent():
    first = _proposal("first", "agent-a", 0.9)
    second = _proposal("second", "agent-a", 0.5)

    resolved = ActionResolver().resolve([second, first], current_world_revision=4)

    assert [(item.action.proposal_id, item.accepted) for item in resolved] == [
        ("first", True),
        ("second", False),
    ]


def test_resolved_action_is_immutable_and_validates_fields():
    action = _proposal("p1", "agent-a", 0.8)
    resolved = ResolvedAction(action, True, "selected")

    with pytest.raises(FrozenInstanceError):
        resolved.accepted = False
    with pytest.raises(ValueError, match="reason"):
        ResolvedAction(action, False, " ")


def test_resolver_does_not_execute_actions_or_write_world_events(tmp_path):
    from cognitive_sandbox.application.world_runtime import WorldRuntime
    from cognitive_sandbox.infrastructure.sqlite_store import SQLiteEventStore

    store = SQLiteEventStore(tmp_path / "resolver.sqlite3")
    world = WorldRuntime(
        store,
        world_id="harbor",
        branch_id="main",
        breakable_object_ids={"cup_001"},
    )
    proposal = _proposal("p1", "agent-a", 0.8, revision=0)

    resolved = ActionResolver().resolve([proposal], current_world_revision=0)

    assert resolved[0].accepted is True
    assert store.list_world_events("harbor") == []
    assert world.world_revision == 0
