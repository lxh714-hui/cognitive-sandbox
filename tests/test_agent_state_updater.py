from dataclasses import FrozenInstanceError

import pytest

from cognitive_sandbox.application.agent_state_updater import AgentStateUpdater
from cognitive_sandbox.domain.agent_state import AgentDynamicState
from cognitive_sandbox.domain.world_events import WorldEvent


def event(event_type):
    return WorldEvent("event-1", "main", "world-1", event_type, "agent-1", {}, 1)


def state(confidence=0.5, stress=0.2, motivation=0.4):
    return AgentDynamicState("agent-1", confidence, stress, motivation)


def test_help_event_increases_confidence_and_motivation():
    original = state()

    updated = AgentStateUpdater().update(original, event("help_attempt"))

    assert updated == AgentDynamicState("agent-1", 0.55, 0.2, 0.45)
    assert updated is not original


def test_protect_event_increases_confidence_and_stress():
    updated = AgentStateUpdater().update(state(), event("protect_attempt"))

    assert updated == AgentDynamicState("agent-1", 0.6, 0.25, 0.4)


def test_observe_event_increases_motivation():
    updated = AgentStateUpdater().update(state(), event("observe_action"))

    assert (updated.confidence, updated.stress, updated.motivation) == pytest.approx(
        (0.5, 0.2, 0.42)
    )


def test_failed_action_reduces_confidence_and_increases_stress():
    updated = AgentStateUpdater().update(state(), event("action_failed"))

    assert (updated.confidence, updated.stress, updated.motivation) == pytest.approx(
        (0.4, 0.3, 0.4)
    )


@pytest.mark.parametrize(
    ("initial", "event_type", "expected"),
    [
        ((0.98, 0.98, 0.98), "protect_attempt", (1.0, 1.0, 0.98)),
        ((0.02, 0.98, 0.02), "action_failed", (0.0, 1.0, 0.02)),
        ((0.98, 0.02, 0.99), "help_attempt", (1.0, 0.02, 1.0)),
    ],
)
def test_updated_values_are_clamped_to_unit_interval(initial, event_type, expected):
    updated = AgentStateUpdater().update(state(*initial), event(event_type))

    assert (updated.confidence, updated.stress, updated.motivation) == pytest.approx(expected)
    assert all(0.0 <= value <= 1.0 for value in expected)


def test_unknown_event_returns_equal_but_new_state():
    original = state()

    updated = AgentStateUpdater().update(original, event("unrecognized"))

    assert updated == original
    assert updated is not original


def test_original_state_is_unchanged_and_model_is_immutable():
    original = state()
    updated = AgentStateUpdater().update(original, event("help_attempt"))

    assert original == AgentDynamicState("agent-1", 0.5, 0.2, 0.4)
    with pytest.raises(FrozenInstanceError):
        updated.confidence = 0.9


def test_dynamic_state_validates_identity_and_ranges():
    with pytest.raises(ValueError, match="character_id"):
        AgentDynamicState(" ", 0.5, 0.5, 0.5)
    with pytest.raises(ValueError, match="confidence"):
        AgentDynamicState("agent", 1.1, 0.5, 0.5)
