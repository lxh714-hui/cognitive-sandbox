from copy import deepcopy

from cognitive_sandbox.application.game_launcher import GameLauncher
from cognitive_sandbox.authority import AuthorityLevel
from cognitive_sandbox.persistence.world_serializer import WorldSerializer
from cognitive_sandbox.persistence.models.save_metadata import SaveMetadata
from cognitive_sandbox.application.world_library import WorldLibrary
from cognitive_sandbox.persistence.storage.save_repository import JsonSaveRepository
from cognitive_sandbox.persistence.world_save_service import WorldSaveService


def _metadata(session):
    return SaveMetadata(
        session.world_instance_id, session.executor.world_id, session.scenario.scenario_id,
        "世界", "简介", "created", "played",
    )


def test_authorities_round_trip_and_legacy_saves_receive_defaults():
    session = GameLauncher().start_scenario("example_world")
    serializer = WorldSerializer()
    payload = serializer.serialize_world(_metadata(session), session)
    restored = serializer.deserialize_world(payload)
    assert restored["session"]["player_character_id"] == session.player_character_id
    assert restored["authority"]["authorities"] == tuple(session.authority_manager.authorities.values())

    legacy = deepcopy(payload)
    legacy.pop("authority")
    legacy["session"]["$mapping"] = [
        pair for pair in legacy["session"]["$mapping"] if pair[0] != "player_character_id"
    ]
    result = serializer.deserialize_world(legacy)
    assert result["authority"]["player_character_id"] == session.player_id
    assert sum(item.authority_level is AuthorityLevel.PLAYER for item in result["authority"]["authorities"]) == 1


def test_player_identity_and_authorities_survive_world_library_restore(tmp_path):
    launcher = GameLauncher()
    service = WorldSaveService(JsonSaveRepository(tmp_path / "saves"))
    library = WorldLibrary(service, launcher.restore_saved_world)
    session = launcher.start_scenario("example_world")
    world = library.register(session)
    player_id = session.player_character_id
    assert world.player_character_id == player_id

    restarted_launcher = GameLauncher()
    restored_library = WorldLibrary(
        WorldSaveService(JsonSaveRepository(tmp_path / "saves")),
        restarted_launcher.restore_saved_world,
    )
    listed_world = restored_library.list_worlds()[0]
    assert listed_world.player_character_id == player_id
    restored, _messages = restored_library.activate(world.instance_id)
    assert restored.player_character_id == player_id
    assert restored.authority_manager.authority_for(player_id).authority_level is AuthorityLevel.PLAYER

