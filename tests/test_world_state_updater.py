from dataclasses import FrozenInstanceError

import pytest

from cognitive_sandbox.application.world_state_updater import WorldStateUpdater
from cognitive_sandbox.domain.world_events import WorldEvent
from cognitive_sandbox.domain.world_transition import WorldStateTransition


def event(event_type):
    return WorldEvent(
        event_id=f"event-{event_type}",
        branch_id="main",
        world_id="world-1",
        event_type=event_type,
        actor_id="agent-1",
        payload={},
        world_revision=1,
    )


@pytest.mark.parametrize(
    ("event_type", "expected"),
    [
        ("help_attempt", {"social_trust": 0.1}),
        ("protect_attempt", {"danger_level": -0.1}),
        ("observe_action", {"information_level": 0.1}),
        ("action_failed", {"failure_count": 1}),
    ],
)
def test_known_event_types_produce_expected_state_delta(event_type, expected):
    transition = WorldStateUpdater().update(event(event_type), {"existing": "unchanged"})

    assert transition.event_id == f"event-{event_type}"
    assert dict(transition.changed_state) == expected


def test_unknown_event_returns_empty_change():
    transition = WorldStateUpdater().update(event("unrecognized"), {})
    assert transition.changed_state == {}


def test_transition_is_immutable_and_deeply_freezes_state():
    transition = WorldStateTransition("event-1", {"nested": {"items": ["value"]}})

    with pytest.raises(FrozenInstanceError):
        transition.event_id = "changed"
    with pytest.raises(TypeError):
        transition.changed_state["nested"]["items"] = ()
    with pytest.raises(TypeError):
        transition.changed_state["nested"]["items"][0] = "changed"


def test_updater_does_not_mutate_input_world_state():
    world_state = {"social_trust": 0.4, "nested": {"values": [1]}}
    snapshot = {"social_trust": 0.4, "nested": {"values": [1]}}

    WorldStateUpdater().update(event("help_attempt"), world_state)

    assert world_state == snapshot

