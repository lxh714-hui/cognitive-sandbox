from dataclasses import FrozenInstanceError

import pytest

from cognitive_sandbox.encounter import (
    CognitionCondition, EmotionCondition, GoalCondition, LocationCondition,
    RelationshipCondition, TimeCondition,
)


def test_encounter_conditions_cover_location_time_goal_relationship_emotion_cognition():
    conditions = (
        LocationCondition("market", "market", True), TimeCondition("t1", "t1", True),
        GoalCondition("buy food", "investigate", True), RelationshipCondition(),
        EmotionCondition(.7, .6, True), CognitionCondition("analytical", "intuitive", True),
    )
    assert all(item.passed for item in conditions)
    with pytest.raises(FrozenInstanceError):
        conditions[0].passed = False
    with pytest.raises(ValueError):
        EmotionCondition(1.1, .4)
