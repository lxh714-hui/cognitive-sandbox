from dataclasses import FrozenInstanceError

import pytest

from cognitive_sandbox.director import DirectorConstraint, DirectorConstraintStatus, DirectorIntent, DirectorIntentType


def test_director_constraint_is_immutable_and_starts_pending():
    intent = DirectorIntent(DirectorIntentType.CHARACTER_ENTRY, "liuyiyi", "引导柳依依登场")
    constraint = DirectorConstraint("dc1", intent, "liuyiyi", .7, ("no_teleportation",))
    assert constraint.status is DirectorConstraintStatus.PENDING
    assert constraint.conditions == ("no_teleportation",)
    with pytest.raises(FrozenInstanceError):
        constraint.status = DirectorConstraintStatus.ACTIVE
