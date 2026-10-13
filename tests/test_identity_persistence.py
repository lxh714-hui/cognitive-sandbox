from cognitive_sandbox.application.game_launcher import GameLauncher
from cognitive_sandbox.identity import CharacterIdentity, IdentityManager
from cognitive_sandbox.persistence.models.save_metadata import SaveMetadata
from cognitive_sandbox.persistence.world_serializer import WorldSerializer


def test_identity_snapshots_round_trip_and_restore_by_stable_character_id():
    launcher = GameLauncher()
    session = launcher.start_scenario("example_world")
    identities = [CharacterIdentity(cid, "显示名" if cid == session.player_id else name,
                                    name, editable=True, naming_source="generated")
                  for cid, name in ((context.character_id, getattr(context.character_state, "name", context.character_id))
                                    for context in session.agent_contexts)]
    session.identity_manager = IdentityManager(identities)
    original_ids = tuple(item.character_id for item in session.agent_contexts)
    metadata = SaveMetadata(session.world_instance_id, session.executor.world_id, "example_world",
                            "world", "description", "created", "played")
    serializer = WorldSerializer()
    decoded = serializer.deserialize_world(serializer.serialize_world(metadata, session))
    restored = launcher.restore_saved_world(decoded)
    assert restored.identity_manager.get(session.player_id).display_name == "显示名"
    assert tuple(item.character_id for item in restored.agent_contexts) == original_ids
    assert restored.identity_manager.get(session.player_id).original_name


def test_old_save_without_identity_data_gets_safe_default_identity():
    session = GameLauncher().start_scenario("example_world")
    assert session.identity_manager.get(session.player_id).character_id == session.player_id


def test_goal_lifecycle_and_development_snapshots_round_trip():
    from cognitive_sandbox.domain.world_events import WorldEvent

    launcher = GameLauncher()
    session = launcher.start_scenario("example_world")
    session.executor.event_pipeline.publish(WorldEvent(
        "development-event", "main", session.executor.world_id, "anomaly_observed",
        session.player_id, {"description": "亲历线索"}, 1,
    ))
    session.goal_lifecycle_manager.evaluate(source_event_id="development-event")
    metadata = SaveMetadata(session.world_instance_id, session.executor.world_id, "example_world",
                            "world", "description", "created", "played")
    serializer = WorldSerializer()
    decoded = serializer.deserialize_world(serializer.serialize_world(metadata, session))
    assert decoded["autonomous"]["development_states"]
    assert decoded["autonomous"]["goal_lifecycle"] == session.goal_lifecycle_manager.snapshot()
    restored = launcher.restore_saved_world(decoded)
    assert restored.development_engine.get(session.player_id).records
    assert restored.goal_lifecycle_manager.snapshot() == session.goal_lifecycle_manager.snapshot()
