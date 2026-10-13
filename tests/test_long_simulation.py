from cognitive_sandbox.application.game_launcher import GameLauncher
from tools.simulation_test.long_simulation_runner import LongSimulationRunner
from tools.simulation_test.simulation_comparison import SimulationComparator


def test_long_runner_advances_cumulative_natural_checkpoints_without_probe_injection():
    session = GameLauncher().start_world("anchor")
    result = LongSimulationRunner().run_world(checkpoints=(1, 4), random_seed=11, session=session)
    assert result.checkpoints == (1, 4)
    assert len(result.reports) == 2
    assert sum(event.event_type.startswith("npc_") for event in result.reports[0].events) > 0
    assert all(report.player_idle_enabled for report in result.reports)
    assert tuple(item.day for item in result.checkpoint_results) == (1, 4)
    assert result.checkpoint_results[1].cumulative_event_count >= result.checkpoint_results[0].cumulative_event_count
    assert result.checkpoint_results[1].npc_action_counts
    assert result.checkpoint_results[1].emergence_report.event_count == result.checkpoint_results[1].cumulative_event_count
    comparison = SimulationComparator().compare(*result.checkpoint_results, 1, 4)
    assert comparison.left_day == 1 and comparison.right_day == 4
    assert comparison.event_delta >= 0
