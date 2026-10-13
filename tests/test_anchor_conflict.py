from cognitive_sandbox.application.game_launcher import GameLauncher
from cognitive_sandbox.simulation_test.simulation_runner import SimulationRunner


def test_anchor_reports_conflict_snapshots_without_leaking_other_knowledge():
    session = GameLauncher().start_anchor_world()
    report = SimulationRunner().run(session, tick_count=2, random_seed=413)
    assert report.ticks == 2
    assert hasattr(report.metrics, "active_conflicts")
    assert report.metrics.knowledge_leaks == 0
    assert report.conflicts == session.conflict_manager.conflicts
