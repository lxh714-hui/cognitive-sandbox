from dataclasses import FrozenInstanceError

import pytest

from cognitive_sandbox.authority import AuthorityLevel, CharacterAuthority


def test_character_authority_levels_and_flags_are_validated_and_immutable():
    player = CharacterAuthority.player("liang")
    important = CharacterAuthority.important_character("liu")
    background = CharacterAuthority.background_character("extra")
    assert player.authority_level is AuthorityLevel.PLAYER
    assert player.controllable and not player.can_make_autonomous_decisions
    assert important.authority_level is AuthorityLevel.IMPORTANT_CHARACTER
    assert not important.controllable and important.can_make_autonomous_decisions
    assert background.authority_level is AuthorityLevel.BACKGROUND_CHARACTER
    with pytest.raises(FrozenInstanceError):
        player.controllable = False


def test_authority_hierarchy_orders_debug_above_director_and_player():
    assert AuthorityLevel.DEBUG > AuthorityLevel.DIRECTOR > AuthorityLevel.PLAYER
    assert AuthorityLevel.PLAYER > AuthorityLevel.IMPORTANT_CHARACTER > AuthorityLevel.BACKGROUND_CHARACTER
