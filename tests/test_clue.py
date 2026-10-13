import pytest

from cognitive_sandbox.information import Clue


def test_clue_is_immutable_and_validates_reliability():
    clue = Clue("c1", "e1", "sound", .7, content="听见街区有异响")
    with pytest.raises((AttributeError, TypeError)):
        clue.content = "完整真相"
    with pytest.raises(ValueError):
        Clue("c2", "e1", "sound", 1.2)


def test_clue_is_not_required_to_contain_a_full_fact():
    clue = Clue("c1", "e1", "sound", .5, content="有人听见奇怪声音")
    assert "原因未知" not in clue.content
