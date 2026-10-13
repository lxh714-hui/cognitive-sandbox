from cognitive_sandbox.application.game_launcher import GameLauncher
from cognitive_sandbox.domain.world_events import WorldEvent


def test_anchor_runtime_propagates_only_public_observed_clues():
    session = GameLauncher().start_anchor_world()
    event = WorldEvent("anchor-info-probe", "main", session.executor.world_id,
                       "anomaly_observed", "liangjing",
                       {"description": "梁景在附近听见钟声异常。", "importance": .7},
                       0, location="liangjing_home", timestamp=session.executor.world_clock.current_time().isoformat())
    session.executor.event_pipeline.publish(event)
    assert session.information_manager.clues
    records = session.knowledge_store.query("liangjing")
    assert any(record.source.source_type == "information" for record, _ in records)
    # The knowledge and rumor service never distributes to every character in a world.
    assert session.information_manager.public_recent_for("liangjing")
