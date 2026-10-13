from cognitive_sandbox.application.game_launcher import GameLauncher
from cognitive_sandbox.application.player_action_parser import PlayerActionParser
from cognitive_sandbox.domain.world_events import WorldEvent
from cognitive_sandbox.persistence.models.save_metadata import SaveMetadata
from cognitive_sandbox.persistence.world_serializer import WorldSerializer
from cognitive_sandbox.time.world_clock import WorldClockState


def test_autonomous_clock_goals_scheduler_and_pending_events_round_trip():
    launcher = GameLauncher(action_interpreter=PlayerActionParser())
    session = launcher.start_scenario("example_world")
    executor = session.executor
    executor.world_clock.restore("2031-04-05T09:30:00+00:00")
    pending = WorldEvent("future-1", "main", executor.world_id, "supply_arrived", "system", {}, 0)
    executor.time_scheduler.schedule(pending, "2031-04-05T10:00:00+00:00", schedule_id="supply")
    metadata = SaveMetadata(
        session.world_instance_id, executor.world_id, "example_world", "灰港", "简介",
        "2031-01-01", "2031-04-05", "active", "running",
    )

    serializer = WorldSerializer()
    decoded = serializer.deserialize_world(serializer.serialize_world(metadata, session))
    autonomous = decoded["autonomous"]

    assert autonomous["clock_state"] == WorldClockState("2031-04-05T09:30:00+00:00")
    assert autonomous["goals"] == executor.goal_manager.goals
    assert autonomous["pending_events"][0].event == pending
    restored = launcher.restore_saved_world(decoded)
    assert restored.executor.world_clock.current_time().isoformat() == "2031-04-05T09:30:00+00:00"
    assert restored.executor.time_scheduler.pending_events[0].event == pending


def test_old_save_without_autonomous_section_defaults_safely():
    launcher = GameLauncher(action_interpreter=PlayerActionParser())
    session = launcher.start_scenario("example_world")
    metadata = SaveMetadata(session.world_instance_id, session.executor.world_id, "example_world", "旧世界", "简介", "d1", "d1", "active", "运行中")
    serializer = WorldSerializer()
    payload = serializer.serialize_world(metadata, session)
    payload.pop("autonomous")
    restored = serializer.deserialize_world(payload)
    assert restored["autonomous"]["goals"] == ()
    assert restored["autonomous"]["clock_state"] is None
