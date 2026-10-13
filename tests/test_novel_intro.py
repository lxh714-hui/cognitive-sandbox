from cognitive_sandbox.application.game_launcher import GameLauncher
from cognitive_sandbox.application.player_action_parser import PlayerActionParser
from cognitive_sandbox.presentation.scenario_presenter import ScenarioPresenter


def test_opening_is_one_natural_paragraph_with_identity_and_scene():
    session = GameLauncher(action_interpreter=PlayerActionParser()).start_scenario("example_world")
    opening = ScenarioPresenter().opening(session)

    assert "\n" not in opening
    assert "灰港纪元" in opening
    assert "灾难后的海港城市" in opening
    assert "港区旧诊所大厅" in opening
    assert "你是玩家" not in opening
    assert "地点：" not in opening and "时间：" not in opening
    assert "energy_level" not in opening and "doctor" not in opening
