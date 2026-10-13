from dataclasses import FrozenInstanceError

import pytest

from cognitive_sandbox.relationship.lifecycle import RelationshipMemory


def test_relationship_memory_preserves_source_and_immutable_impact():
    impact = {"trust": 15}
    memory = RelationshipMemory("liuyiyi", "liangjing", "event_shared", "cooperate", impact, "day-2")
    impact["trust"] = 99
    assert memory.impact["trust"] == 15
    with pytest.raises(TypeError):
        memory.impact["trust"] = 4
    with pytest.raises(FrozenInstanceError):
        memory.source_event = "other"

