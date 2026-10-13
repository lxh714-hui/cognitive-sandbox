import pytest

from cognitive_sandbox.authority import AuthorityError, AuthorityManager, CharacterAuthority


def test_world_has_only_one_player_character():
    manager = AuthorityManager((CharacterAuthority.player("player"),), player_character_id="player")
    with pytest.raises(AuthorityError, match="only one"):
        manager.register(CharacterAuthority.player("second"))


def test_roleplay_session_binds_player_character_id():
    from cognitive_sandbox.application.game_launcher import GameLauncher
    session = GameLauncher().start_scenario("example_world")
    assert session.player_character_id == session.player_id
    with pytest.raises(AttributeError):
        session.player_character_id = "doctor"
