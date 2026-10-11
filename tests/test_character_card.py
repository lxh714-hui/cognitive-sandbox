from dataclasses import FrozenInstanceError

import pytest

from cognitive_sandbox.application.character_card_loader import CharacterCardLoader
from cognitive_sandbox.domain.character_card import CharacterCard
from cognitive_sandbox.domain.constraint import Constraint


def test_character_card_creation_and_tuple_fields_are_immutable():
    personality = ["冷静", "谨慎"]
    goals = ["保护同伴"]
    constraints = [Constraint("hard", "不会伤害无辜者")]
    card = CharacterCard(
        "captain", "林夏", 28, "女", "医生", personality,
        "灾难前在医院工作。", goals, constraints, "portraits/linxia.png",
    )

    personality.append("冲动")
    goals.clear()
    constraints.clear()
    assert card.personality == ("冷静", "谨慎")
    assert card.goals == ("保护同伴",)
    assert card.constraints == (Constraint("hard", "不会伤害无辜者"),)
    assert card.portrait == "portraits/linxia.png"
    with pytest.raises(FrozenInstanceError):
        card.name = "其他角色"


def test_character_card_rejects_invalid_identity_lists_and_constraints():
    with pytest.raises(ValueError, match="character_id"):
        CharacterCard("", "林夏")
    with pytest.raises(ValueError, match="personality"):
        CharacterCard("captain", "林夏", personality=("",))
    with pytest.raises(TypeError, match="goals"):
        CharacterCard("captain", "林夏", goals="保护同伴")
    with pytest.raises(ValueError, match="type"):
        Constraint("secret", "隐藏约束")
    with pytest.raises(TypeError, match="Constraint"):
        CharacterCard("captain", "林夏", constraints=("hard",))


def test_character_card_loader_returns_registered_immutable_card():
    card = CharacterCard("captain", "林夏", personality=("冷静",), goals=("帮助他人",))
    loader = CharacterCardLoader((card,))

    assert loader.load("captain") is card
    assert loader.load("unknown") is None
