from dataclasses import FrozenInstanceError

import pytest

from cognitive_sandbox.application.character_initializer import (
    CharacterInitializationRequest,
    CharacterInitializer,
)
from cognitive_sandbox.domain.character import CharacterState


def test_young_doctor_uses_doctor_template():
    character = CharacterInitializer(character_id_factory=lambda: "doctor-1").initialize(
        CharacterInitializationRequest("年轻医生")
    )

    assert character.character_id == "doctor-1"
    assert character.name == "年轻医生"
    assert character.role == "医生"
    assert character.traits == ("谨慎", "富有同情心")
    assert character.goals == ("帮助他人",)
    assert character.fears
    assert character.memories == ()


def test_soldier_template_preserves_multiple_traits_and_goals():
    character = CharacterInitializer(character_id_factory=lambda: "soldier-1").initialize(
        CharacterInitializationRequest("士兵")
    )

    assert character.role == "士兵"
    assert character.traits == ("勇敢", "纪律性")
    assert character.goals == ("保护同伴", "完成职责")


def test_unknown_description_uses_generic_character_template():
    character = CharacterInitializer(character_id_factory=lambda: "resident-1").initialize(
        CharacterInitializationRequest("来自云端的旅人")
    )

    assert character.role == "普通居民"
    assert character.traits == ("适应力强",)
    assert character.character_id == "resident-1"


@pytest.mark.parametrize("prompt", ["", "  ", None])
def test_empty_prompt_is_rejected(prompt):
    with pytest.raises(ValueError, match="prompt"):
        CharacterInitializationRequest(prompt)


def test_character_state_is_immutable_and_normalizes_sequence_fields():
    character = CharacterState(
        "character-1",
        "林夏",
        "医生",
        ["冷静", "细心"],
        ["调查", "帮助他人"],
        [],
        [],
    )

    assert character.traits == ("冷静", "细心")
    assert character.goals == ("调查", "帮助他人")
    with pytest.raises(FrozenInstanceError):
        character.role = "士兵"


def test_character_state_rejects_empty_identity_fields():
    with pytest.raises(ValueError, match="character_id"):
        CharacterState(" ", "名字", "角色", (), (), (), ())
    with pytest.raises(ValueError, match="name"):
        CharacterState("id", " ", "角色", (), (), (), ())
