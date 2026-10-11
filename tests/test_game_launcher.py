import pytest

from cognitive_sandbox.application.game_launcher import GameLauncher
from cognitive_sandbox.application.roleplay_session import RoleplaySession


def test_game_launcher_bootstraps_selected_scenario_into_roleplay_session():
    launcher = GameLauncher()

    session = launcher.start_scenario("post_apocalypse_city")

    assert isinstance(session, RoleplaySession)
    assert session.player_id == "doctor"
    assert session.current_turn.status == "waiting_input"
    assert session.world_state == {"danger_level": 0.5, "resource_level": 0.3}
    assert launcher.current_session is session


def test_game_launcher_rejects_unknown_scenario():
    with pytest.raises(ValueError, match="unknown scenario"):
        GameLauncher().start_scenario("missing")
