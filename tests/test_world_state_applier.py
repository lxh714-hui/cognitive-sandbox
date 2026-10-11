import pytest

from cognitive_sandbox.application.world_state_applier import WorldStateApplier
from cognitive_sandbox.domain.world_transition import WorldStateTransition


def test_numeric_delta_is_applied_to_existing_field():
    result = WorldStateApplier().apply(
        {"social_trust": 0.5},
        WorldStateTransition("event-1", {"social_trust": 0.1}),
    )

    assert result["social_trust"] == pytest.approx(0.6)


def test_missing_numeric_field_is_created_from_delta():
    result = WorldStateApplier().apply(
        {},
        WorldStateTransition("event-1", {"danger_level": -0.1}),
    )

    assert result["danger_level"] == pytest.approx(-0.1)


def test_non_numeric_transition_value_overwrites_field():
    result = WorldStateApplier().apply(
        {"status": "old", "untouched": "keep"},
        WorldStateTransition("event-1", {"status": "changed"}),
    )

    assert result["status"] == "changed"
    assert result["untouched"] == "keep"


def test_input_world_state_is_not_modified_or_shared():
    source = {"nested": {"items": ["original"]}, "counter": 2}
    result = WorldStateApplier().apply(
        source,
        WorldStateTransition("event-1", {"counter": 1}),
    )

    assert source == {"nested": {"items": ["original"]}, "counter": 2}
    assert result is not source
    assert result["counter"] == 3
    assert result["nested"] is not source["nested"]


def test_returned_world_state_is_deeply_read_only():
    result = WorldStateApplier().apply(
        {"nested": {"items": ["original"]}},
        WorldStateTransition("event-1", {"new": {"values": [1]}}),
    )

    with pytest.raises(TypeError):
        result["other"] = "value"
    with pytest.raises(TypeError):
        result["nested"]["extra"] = True
    with pytest.raises(TypeError):
        result["nested"]["items"][0] = "changed"
    with pytest.raises(TypeError):
        result["new"]["values"][0] = 2


def test_empty_transition_returns_unchanged_read_only_copy():
    source = {"value": 1}
    result = WorldStateApplier().apply(source, WorldStateTransition("event-1", {}))

    assert dict(result) == source
    assert result is not source
    with pytest.raises(TypeError):
        result["value"] = 2
