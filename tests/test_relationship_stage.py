from dataclasses import FrozenInstanceError

import pytest

from cognitive_sandbox.relationship.lifecycle import RelationshipStage
from cognitive_sandbox.relationship.lifecycle.relationship_lifecycle_manager import RelationshipStageEntry


def test_relationship_stage_and_stage_entry_are_immutable():
    item = RelationshipStageEntry("liangjing", "liuyiyi", RelationshipStage.STRANGER)
    assert item.stage is RelationshipStage.STRANGER
    with pytest.raises(FrozenInstanceError):
        item.stage = RelationshipStage.CLOSE

