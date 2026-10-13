from cognitive_sandbox.application.game_launcher import GameLauncher
from cognitive_sandbox.application.player_action_parser import PlayerActionParser
from cognitive_sandbox.application.world_library import WorldLibrary
from cognitive_sandbox.domain.world_events import WorldEvent
from cognitive_sandbox.persistence.storage.save_repository import JsonSaveRepository
from cognitive_sandbox.persistence.world_save_service import WorldSaveService
from cognitive_sandbox.relationship.lifecycle import RelationshipStage


def _services(path):
    launcher = GameLauncher(action_interpreter=PlayerActionParser())
    service = WorldSaveService(JsonSaveRepository(path))
    return launcher, service, WorldLibrary(service, launcher.restore_saved_world)


def test_relationship_lifecycle_restores_stages_events_and_memories(tmp_path):
    launcher, _service, library = _services(tmp_path / "saves")
    session = launcher.start_scenario("example_world")
    world = library.register(session)
    manager = session.relationship_lifecycle_manager
    event = WorldEvent("save-talk", event_type="dialogue_event", actor_id=session.player_id,
                       target_id="doctor", payload={})
    manager.handle_event(event)
    expected_stage = manager.stage_for(session.player_id, "doctor")
    library.save_active(())

    _new_launcher, _new_service, restored_library = _services(tmp_path / "saves")
    restored, _messages = restored_library.activate(world.instance_id)
    restored_manager = restored.relationship_lifecycle_manager
    assert restored_manager.stage_for(session.player_id, "doctor") is expected_stage is RelationshipStage.ACQUAINTANCE
    assert restored_manager.events[-1].source_event_id == "save-talk"
    assert restored_manager.memories[-1].source_event == "save-talk"


def test_legacy_missing_relationship_snapshot_defaults_to_empty(tmp_path):
    launcher, service, library = _services(tmp_path / "legacy")
    session = launcher.start_scenario("example_world")
    world = library.register(session)
    library.save_active(())
    payload = service.repository.load_world(world.instance_id)
    autonomous_pairs = payload["autonomous"]["$mapping"]
    payload["autonomous"]["$mapping"] = [pair for pair in autonomous_pairs
                                           if pair[0] != "relationship_lifecycle"]
    restored = service.serializer.deserialize_world(payload)
    assert restored["autonomous"]["relationship_lifecycle"].stages == ()

