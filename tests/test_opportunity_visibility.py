from datetime import datetime, timezone

from cognitive_sandbox.conflict.conflict_state import ConflictState
from cognitive_sandbox.conflict.conflict_type import ConflictType
from cognitive_sandbox.narrative.opportunity import EventEmergenceEvaluator, OpportunityManager


def test_conflict_opportunity_is_visible_only_to_participants():
    conflict = ConflictState("private-conflict", ConflictType.INFORMATION_CONFLICT,
                             ("liangjing", "liuyiyi"), severity=.9)
    manager = OpportunityManager()
    manager.refresh(world_time=datetime(2026, 1, 1, tzinfo=timezone.utc), active_conflicts=(conflict,))
    assert len(manager.visible_to("liangjing")) == 1
    assert len(manager.visible_to("liuyiyi")) == 1
    assert manager.visible_to("outsider") == ()


def test_hidden_information_never_becomes_a_public_opportunity():
    candidates = EventEmergenceEvaluator().evaluate(
        world_time="2026-01-01T00:00:00+00:00",
        information_by_character={"liangjing": ({"content": "secret basement", "confidence": .95},)},
    )
    assert candidates
    assert all(item.visibility == "owner" for item in candidates)
    assert all("secret basement" not in item.description for item in candidates)
