from cognitive_sandbox.application.game_launcher import GameLauncher
from cognitive_sandbox.simulation_test.long_simulation_runner import LongSimulationRunner
from cognitive_sandbox.persistence.models.save_metadata import SaveMetadata
from cognitive_sandbox.persistence.world_serializer import WorldSerializer


def test_anchor_world_starts_separate_player_and_npc_tracks_and_runs_naturally():
    session = GameLauncher().start_anchor_world()
    assert session.presence_manager.get("liangjing").current_location == session.world_state["location"]
    assert session.presence_manager.get("liuyiyi").availability.value == "UNKNOWN"
    assert not session.executor.event_timeline.events
    result = LongSimulationRunner().run_anchor(checkpoints=(2,), session=session)
    report = result.reports[0]
    assert any(event.event_type.startswith("npc_") for event in report.events)
    assert report.metrics.knowledge_leaks == 0
    assert report.thread_states
    assert any(clue.content_type == "neighborhood_rumor" for clue in session.information_manager.clues)
    metadata = SaveMetadata(
        session.world_instance_id, session.executor.world_id, "anchor_world", "锚点", "模拟观察",
        session.anchor_started_at, session.executor.world_clock.current_time().isoformat(),
        player_character_id="liangjing",
    )
    saved = WorldSerializer().serialize_world(metadata, session)
    package_state = WorldSerializer().deserialize_world(saved)["autonomous"]["world_package"]
    assert package_state["content_version"] == session.anchor_content_version
    assert package_state["summary"]["event_count"] == len(session.executor.event_timeline.events)
    assert package_state["replay_index"] == len(session.executor.event_timeline.events)
    assert package_state["settings"] == session.anchor_world_settings
    assert set(package_state["routines"]) == {"liangjing", "liuyiyi", "song", "pei"}
