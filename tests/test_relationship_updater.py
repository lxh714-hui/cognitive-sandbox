from dataclasses import FrozenInstanceError

import pytest

from cognitive_sandbox.application.relationship_updater import RelationshipUpdater
from cognitive_sandbox.domain.relationship import RelationshipState
from cognitive_sandbox.domain.world_events import WorldEvent


def make_event(event_type):
    return WorldEvent("event-1", "main", "world-1", event_type, "agent-1", {}, 1)


def test_help_event_increases_care_trust():
    care = RelationshipState("agent-1", "patient", "care", 0.6)

    updated = RelationshipUpdater().update((care,), make_event("help_attempt"))

    assert updated[0].trust == pytest.approx(0.7)
    assert updated[0] is not care


def test_protect_event_increases_comrade_trust():
    comrade = RelationshipState("agent-1", "ally", "comrade", 0.8)

    updated = RelationshipUpdater().update((comrade,), make_event("protect_attempt"))

    assert updated[0].trust == pytest.approx(0.85)


def test_failed_action_decreases_all_existing_relationship_trust():
    relations = (
        RelationshipState("agent-1", "patient", "care", 0.6),
        RelationshipState("agent-1", "ally", "comrade", 0.8),
    )

    updated = RelationshipUpdater().update(relations, make_event("action_failed"))

    assert tuple(item.trust for item in updated) == pytest.approx((0.55, 0.75))


@pytest.mark.parametrize(
    ("relation_type", "trust", "event_type", "expected"),
    [
        ("care", 0.95, "help_attempt", 1.0),
        ("comrade", 0.99, "protect_attempt", 1.0),
        ("care", 0.0, "action_failed", 0.0),
    ],
)
def test_trust_is_clamped_to_supported_range(relation_type, trust, event_type, expected):
    relation = RelationshipState("agent-1", "target", relation_type, trust)

    updated = RelationshipUpdater().update((relation,), make_event(event_type))

    assert updated[0].trust == expected
    assert 0.0 <= updated[0].trust <= 1.0


@pytest.mark.parametrize("event_type", ["observe_action", "unknown_event"])
def test_unrelated_event_leaves_relationship_unchanged(event_type):
    relation = RelationshipState("agent-1", "target", "care", 0.6)

    updated = RelationshipUpdater().update((relation,), make_event(event_type))

    assert updated == (relation,)
    assert updated[0] is relation


def test_missing_matching_relation_keeps_relationship_unchanged():
    relation = RelationshipState("agent-1", "ally", "comrade", 0.8)

    updated = RelationshipUpdater().update((relation,), make_event("help_attempt"))

    assert updated == (relation,)
    assert updated[0] is relation


def test_original_relationship_is_unchanged_and_updated_value_is_immutable():
    relation = RelationshipState("agent-1", "patient", "care", 0.6)
    updated = RelationshipUpdater().update((relation,), make_event("help_attempt"))

    assert relation.trust == 0.6
    with pytest.raises(FrozenInstanceError):
        updated[0].trust = 0.9
    with pytest.raises(AttributeError):
        updated.append(relation)
