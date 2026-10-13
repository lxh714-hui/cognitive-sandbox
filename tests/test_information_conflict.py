from types import SimpleNamespace

from cognitive_sandbox.conflict import ConflictManager, ConflictType


def test_information_conflict_uses_character_scoped_views_and_safe_description():
    manager = ConflictManager()
    states = manager.refresh(knowledge_by_character={
        "a": (SimpleNamespace(fact_id="rumor-anomaly", known_content="异常传闻"),),
        "b": (SimpleNamespace(fact_id="rumor-anomaly", known_content="异常线索"),),
        "c": (),
    })
    state = next(item for item in states if item.conflict_type is ConflictType.INFORMATION_CONFLICT)
    assert state.participants == ("a", "b")
    assert "异常线索" not in state.description
    assert "c" not in state.participants
