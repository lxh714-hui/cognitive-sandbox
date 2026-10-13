from cognitive_sandbox.application.game_launcher import GameLauncher
from tools.simulation_test.long_simulation_runner import LongSimulationRunner
from tools.simulation_test.story_emergence_report import StoryEmergenceAnalyzer


def test_emergence_report_uses_recorded_clue_paths_and_autonomous_decisions():
    session = GameLauncher().start_world("anchor")
    result = LongSimulationRunner().run_world(checkpoints=(3,), random_seed=2, session=session)
    emergence = StoryEmergenceAnalyzer().analyze(result.reports[0], session)
    assert emergence.event_count == len(result.reports[0].events)
    assert emergence.chains
    assert dict(emergence.character_activity).get("liuyiyi", 0) > 0
    assert 0 <= emergence.emergence_score <= 1
