from dataclasses import FrozenInstanceError

import pytest

from cognitive_sandbox.application.action_event_adapter import ActionEventAdapter
from cognitive_sandbox.domain.actions import ActionCandidate, ResolvedActionResult
from cognitive_sandbox.domain.world_events import WorldEvent


def make_action(intent, action_id=None):
    return ActionCandidate(
        action_id=action_id or f"action-{intent}",
        actor_id="agent-1",
        intent=intent,
        motivation="test",
    )


def make_adapter():
    return ActionEventAdapter(
        world_id="world-1",
        branch_id="main",
        world_revision=4,
        event_id_factory=lambda: "event-1",
    )


@pytest.mark.parametrize(
    ("intent", "event_type"),
    [("help", "help_attempt"), ("protect", "protect_attempt"), ("observe", "observe_action")],
)
def test_successful_action_is_adapted_to_expected_event_type(intent, event_type):
    action = make_action(intent)
    result = ResolvedActionResult(action.action_id, True, "尝试行动", {"kind": "test"})

    event = make_adapter().adapt(result, action)

    assert isinstance(event, WorldEvent)
    assert event.event_type == event_type
    assert event.actor_id == action.actor_id
    assert event.payload["description"] == "尝试行动"


def test_failed_action_is_adapted_as_action_failed():
    action = make_action("unknown")
    result = ResolvedActionResult(action.action_id, False, "行动无法解析", {"error": "unknown_action"})

    event = make_adapter().adapt(result, action)

    assert event.event_type == "action_failed"
    assert event.payload["description"] == "行动无法解析"


def test_impact_is_passed_through_and_event_is_immutable():
    action = make_action("help")
    result = ResolvedActionResult(
        action.action_id,
        True,
        "角色尝试提供帮助",
        {"social": {"effects": ["positive"]}},
    )

    event = make_adapter().adapt(result, action)

    assert event.payload["impact"]["social"]["effects"] == ("positive",)
    with pytest.raises(TypeError):
        event.payload["impact"]["social"]["effects"] = ()
    with pytest.raises(FrozenInstanceError):
        event.event_type = "changed"


def test_adapter_rejects_mismatched_action_result_ids():
    action = make_action("help")
    result = ResolvedActionResult("other-action", True, "尝试行动", {})

    with pytest.raises(ValueError, match="IDs must match"):
        make_adapter().adapt(result, action)
