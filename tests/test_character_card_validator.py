from cognitive_sandbox.application.character_card_validator import CharacterCardValidator
from cognitive_sandbox.domain.character_card import CharacterCard
from cognitive_sandbox.domain.constraint import Constraint


def test_character_card_validator_accepts_valid_card():
    card = CharacterCard(
        "captain", "林夏", personality=("冷静",), goals=("保护同伴",),
        constraints=(Constraint("hard", "不会伤害无辜者"),),
    )

    result = CharacterCardValidator().validate(card)

    assert result.valid
    assert result.errors == ()


def test_character_card_validator_reports_invalid_fields_and_constraint_type():
    bad_constraint = object.__new__(Constraint)
    object.__setattr__(bad_constraint, "type", "secret")
    object.__setattr__(bad_constraint, "content", "隐藏约束")
    card = object.__new__(CharacterCard)
    object.__setattr__(card, "character_id", "")
    object.__setattr__(card, "name", "")
    object.__setattr__(card, "personality", [""])
    object.__setattr__(card, "goals", [""])
    object.__setattr__(card, "constraints", (bad_constraint,))

    result = CharacterCardValidator().validate(card)

    assert not result.valid
    assert any("character_id" in error for error in result.errors)
    assert any("name" in error for error in result.errors)
    assert any("personality" in error for error in result.errors)
    assert any("goals" in error for error in result.errors)
    assert any("type" in error for error in result.errors)
    assert card.constraints == (bad_constraint,)
