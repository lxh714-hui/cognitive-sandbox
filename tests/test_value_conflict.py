from types import SimpleNamespace

from cognitive_sandbox.conflict import ConflictManager, ConflictType
from cognitive_sandbox.cognition.belief_inference import Belief


def test_distinct_interpretations_of_shared_information_create_value_conflict():
    manager = ConflictManager()
    states = manager.refresh(cognition_by_character={
        "a": SimpleNamespace(beliefs=(Belief("fact1", "应优先查明", .6, .5, "a"),)),
        "b": SimpleNamespace(beliefs=(Belief("fact1", "应优先保障安全", .6, .5, "b"),)),
    })
    assert any(item.conflict_type is ConflictType.VALUE_CONFLICT for item in states)
