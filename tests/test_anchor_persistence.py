from cognitive_sandbox.application.game_launcher import GameLauncher
from cognitive_sandbox.application.world_library import WorldLibrary
from cognitive_sandbox.persistence.storage.save_repository import JsonSaveRepository
from cognitive_sandbox.persistence.world_save_service import WorldSaveService
from cognitive_sandbox.presentation.message import DisplayMessage, MessageType


def test_anchor_world_saves_and_restores_knowledge_threads_cognition_and_authority(tmp_path):
    launcher = GameLauncher()
    saves = WorldSaveService(JsonSaveRepository(tmp_path / "saves"))
    library = WorldLibrary(saves, launcher.restore_saved_world)
    session = launcher.start_world("anchor")
    world = library.register(session)
    message = DisplayMessage(MessageType.PLAYER, "观察住所")
    library.save_active((message,))

    restarted = GameLauncher()
    restored_library = WorldLibrary(
        WorldSaveService(JsonSaveRepository(tmp_path / "saves")), restarted.restore_saved_world
    )
    restored, history = restored_library.activate(world.instance_id)
    assert restored.scenario.scenario_id == "anchor"
    assert history == (message,)
    assert restored.authority_manager.player_character_id == "liangjing"
    assert len(restored.executor.cognitive_engine.styles) == 4
    assert {thread.id for thread in restored.narrative_state.threads} == {
        "liangjing_return", "anomaly_investigation", "potential_intersection"
    }
    assert len(restored.knowledge_store.snapshot()[1]) == 7
