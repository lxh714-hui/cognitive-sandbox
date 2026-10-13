from dataclasses import FrozenInstanceError

import pytest

from cognitive_sandbox.director.constraint_type import ConstraintType
from cognitive_sandbox.director.constraint_target import ConstraintTarget
from cognitive_sandbox.director.constraint_strength import ConstraintStrength
from cognitive_sandbox.director.director_intent import DirectorIntent, DirectorIntentType
from cognitive_sandbox.director.director_constraint import DirectorConstraint


def test_constraint_types_targets_and_strengths_are_explicit_and_immutable():
    intent = DirectorIntent(DirectorIntentType.CUSTOM_DIRECTION, None, "希望调查异常", constraint_type="PREFER",
                            constraint_target="NARRATIVE_THREAD", strength="high")
    item = DirectorConstraint("c1", intent, None, .7)
    assert (item.constraint_type, item.target_kind, item.strength) == (
        ConstraintType.PREFER, ConstraintTarget.NARRATIVE_THREAD, ConstraintStrength.HIGH)
    with pytest.raises(FrozenInstanceError):
        item.category = "changed"
