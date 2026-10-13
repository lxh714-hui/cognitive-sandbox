from cognitive_sandbox.application.anchor_world_loader import AnchorWorldLoader
from cognitive_sandbox.application.game_launcher import GameLauncher
from cognitive_sandbox.authority.authority_level import AuthorityLevel
from cognitive_sandbox.character_presence.character_presence import PresenceState


def test_anchor_player_and_important_character_authority():
    package = AnchorWorldLoader().load()
    assert package.authorities["liangjing"].authority_level is AuthorityLevel.PLAYER
    assert package.authorities["liangjing"].controllable
    for character_id in ("liuyiyi", "song", "pei"):
        authority = package.authorities[character_id]
        assert authority.authority_level is AuthorityLevel.IMPORTANT_CHARACTER
        assert not authority.controllable
        assert authority.can_make_autonomous_decisions

    session = GameLauncher().start_anchor_world()
    assert session.authority_manager.player_character_id == "liangjing"
    assert not session.authority_manager.authority_for("liuyiyi").controllable
    assert session.presence_manager.get("liuyiyi").availability is PresenceState.UNKNOWN
    assert session.executor.relationship_manager is not None
