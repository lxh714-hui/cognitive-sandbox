from dataclasses import FrozenInstanceError

import pytest

from cognitive_sandbox.application.event_importance import EventImportanceEvaluator
from cognitive_sandbox.domain.simulation import EventImportance
from cognitive_sandbox.domain.world_events import WorldEvent


def _event(event_type):
    return WorldEvent(
        event_id="event-1",
        branch_id="main",
        world_id="harbor",
        event_type=event_type,
        actor_id="agent-a",
        payload={},
        world_revision=1,
    )


@pytest.mark.parametrize(
    ("event_type", "expected_score", "expected_level"),
    [
        ("BREAK_OBJECT", 0.9, "high"),
        ("OBJECT_BROKEN", 0.9, "high"),
        ("OBJECT_INSPECTED", 0.45, "medium"),
        ("UNCLASSIFIED_EVENT", 0.2, "low"),
    ],
)
def test_event_importance_maps_event_kind_to_deterministic_lod(
    event_type, expected_score, expected_level
):
    result = EventImportanceEvaluator().evaluate(_event(event_type))

    assert result.score == expected_score
    assert result.level == expected_level


def test_event_importance_model_is_immutable_and_validates_values():
    importance = EventImportance(0.75, "high")

    with pytest.raises(FrozenInstanceError):
        importance.level = "low"
    with pytest.raises(ValueError, match="between 0 and 1"):
        EventImportance(1.1, "high")
    with pytest.raises(ValueError, match="low, medium, or high"):
        EventImportance(0.5, "critical")


def test_evaluator_requires_world_event():
    with pytest.raises(TypeError, match="WorldEvent"):
        EventImportanceEvaluator().evaluate("not-an-event")
