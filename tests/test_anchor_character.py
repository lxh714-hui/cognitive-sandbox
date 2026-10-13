from pathlib import Path
from cognitive_sandbox.application.scenario_package_loader import ScenarioPackageLoader
from cognitive_sandbox.application.game_launcher import GameLauncher
from cognitive_sandbox.authority.authority_level import AuthorityLevel
from cognitive_sandbox.character_presence.character_presence import PresenceState


def test_anchor_player_and_important_character_authority():
    content = ScenarioPackageLoader().load(Path(__file__).parents[1] / "assets" / "scenarios" / "anchor")
    profiles = content.scenario.runtime_config["character_profiles"]
    assert profiles["liangjing"]["authority"] == AuthorityLevel.PLAYER.name
    assert profiles["liangjing"]["authority"] == "PLAYER"
    for character_id in ("liuyiyi", "song", "pei"):
        assert profiles[character_id]["authority"] == AuthorityLevel.IMPORTANT_CHARACTER.name

    session = GameLauncher().start_world("anchor")
    assert session.authority_manager.player_character_id == "liangjing"
    assert not session.authority_manager.authority_for("liuyiyi").controllable
    assert session.presence_manager.get("liuyiyi").availability is PresenceState.UNKNOWN
    assert session.executor.relationship_manager is not None
