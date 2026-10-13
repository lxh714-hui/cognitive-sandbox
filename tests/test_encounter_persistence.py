from cognitive_sandbox.encounter import EncounterCandidate, EncounterMemory, EncounterSnapshot, EncounterStatus
from cognitive_sandbox.application.game_launcher import GameLauncher
from cognitive_sandbox.domain.world_events import WorldEvent
from cognitive_sandbox.persistence.models.save_metadata import SaveMetadata
from cognitive_sandbox.persistence.world_serializer import WorldSerializer


def test_encounter_snapshot_round_trips_and_legacy_default_is_empty():
    candidate = EncounterCandidate("a", "b", "market", "t/t", "overlap", .7,
                                   status=EncounterStatus.TRIGGERED, candidate_id="c")
    memory = EncounterMemory("a", "b", "event", "event", "first_contact", "t", "public contact")
    snapshot = EncounterSnapshot((candidate,), (), (memory,), (), ("source",))
    restored = WorldSerializer._decode(WorldSerializer._encode(snapshot))
    assert restored == snapshot
    assert EncounterSnapshot() == EncounterSnapshot((), (), (), (), ())


def test_world_save_restores_encounter_trajectory_and_legacy_empty_state():
    launcher = GameLauncher()
    session = launcher.start_world("anchor")
    now = session.executor.world_clock.current_time().isoformat()
    session.encounter_manager.handle_event(WorldEvent(
        "trajectory-save", "main", session.executor.world_id, "observe_action", "liangjing",
        {"description": "玩家观察周围"}, 0, location="梁景住所", timestamp=now,
    ))
    metadata = SaveMetadata(
        session.world_instance_id, session.executor.world_id, "anchor", "锚点", "测试存档",
        now, now, player_character_id="liangjing",
    )
    serializer = WorldSerializer()
    payload = serializer.serialize_world(metadata, session)
    decoded = serializer.deserialize_world(payload)
    restored = GameLauncher().restore_saved_world(decoded)
    assert restored.encounter_manager.snapshot() == session.encounter_manager.snapshot()

    # Removing the newly added optional key from a version-1 save still yields
    # an empty snapshot, preserving compatibility with older files.
    legacy = dict(payload)
    autonomous = dict(payload["autonomous"])
    encoded_mapping = autonomous["$mapping"]
    autonomous["$mapping"] = [pair for pair in encoded_mapping if pair[0] != "encounters"]
    legacy["autonomous"] = autonomous
    legacy_decoded = serializer.deserialize_world(legacy)
    assert legacy_decoded["autonomous"]["encounters"] == EncounterSnapshot()
