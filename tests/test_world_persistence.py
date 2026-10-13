from dataclasses import replace
import os

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from cognitive_sandbox.application.game_launcher import GameLauncher
from cognitive_sandbox.application.player_action_parser import PlayerActionParser
from cognitive_sandbox.application.world_library import WorldLibrary
from cognitive_sandbox.domain.character_mind import KnowledgeContext, MemoryContext
from cognitive_sandbox.domain.character_card import CharacterCard
from cognitive_sandbox.domain.world_patch import CharacterAddition, WorldPatch, WorldPatchType
from cognitive_sandbox.knowledge.models.knowledge_record import KnowledgeRecord, KnowledgeType
from cognitive_sandbox.knowledge.models.knowledge_source import KnowledgeSource
from cognitive_sandbox.knowledge.models.world_fact import WorldFact
from cognitive_sandbox.persistence.storage.save_repository import JsonSaveRepository
from cognitive_sandbox.persistence.world_save_service import WorldSaveError, WorldSaveService
from cognitive_sandbox.presentation.message import DisplayMessage, MessageType


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture
def qapp():
    return QApplication.instance() or QApplication([])


def _services(tmp_path):
    launcher = GameLauncher(action_interpreter=PlayerActionParser())
    service = WorldSaveService(JsonSaveRepository(tmp_path / "world_saves"))
    library = WorldLibrary(service, launcher.restore_saved_world)
    return launcher, service, library


def _new_session(launcher, marker="post_apocalypse_city"):
    session = launcher.start_scenario(marker)
    session.world_state["day"] = 1
    return session


def _knowledge(session):
    character_id = session.player_id
    fact = WorldFact("fact-known", "医生听见有人敲门", "sound", "day-1", (character_id,), 0.8)
    source = KnowledgeSource("source-known", "observation", "现场观察")
    record = KnowledgeRecord(
        character_id, fact.id, KnowledgeType.OBSERVED, source, 0.8, "day-1", "有人敲门"
    )
    session.knowledge_store.add_fact(fact)
    session.knowledge_store.add_knowledge(record)
    return fact, record


def test_save_reload_restores_world_state_and_multiple_worlds_do_not_overwrite(tmp_path):
    launcher, service, library = _services(tmp_path)
    first = _new_session(launcher)
    first_instance = library.register(first)
    first.world_state["danger_level"] = 0.2
    library.save_active((DisplayMessage("system", "第一世界状态"),))

    second = _new_session(launcher)
    second_instance = library.register(second)
    second.world_state["danger_level"] = 0.9
    library.save_active((DisplayMessage("system", "第二世界状态"),))

    restarted_launcher, _service2, restarted = _services(tmp_path)
    restored_first, first_messages = restarted.activate(first_instance.instance_id)
    restored_second, second_messages = restarted.activate(second_instance.instance_id)

    assert restored_first.world_state["danger_level"] == pytest.approx(0.2)
    assert restored_second.world_state["danger_level"] == pytest.approx(0.9)
    assert first_messages[0].content == "第一世界状态"
    assert second_messages[0].content == "第二世界状态"
    assert restarted_launcher.current_session is restored_second
    assert len(restarted.list_worlds()) == 2


def test_chat_history_and_character_mind_round_trip(tmp_path):
    launcher, _service, library = _services(tmp_path)
    session = _new_session(launcher, "example_world")
    world = library.register(session)
    _, record = _knowledge(session)
    character_id = session.player_id
    old_mind = session.executor.character_minds.get(character_id)
    if old_mind is None:
        from cognitive_sandbox.application.character_mind_builder import CharacterMindBuilder

        card = next(card for card in session.scenario_content.character_cards if card.character_id == character_id)
        old_mind = CharacterMindBuilder().build(card)
    mind = replace(
        old_mind,
        memory_context=MemoryContext(stable_memory=("曾经守过一夜",), recent_memory=("刚听见敲门",)),
        knowledge_context=KnowledgeContext((record,), owner_id=character_id),
    )
    session.executor.restore_character_minds({character_id: mind})
    messages = (
        DisplayMessage(MessageType.PLAYER, "查看门口"),
        DisplayMessage(MessageType.CHARACTER, "门外传来敲门声", speaker_id="沈医生"),
        DisplayMessage(MessageType.SYSTEM, "这一轮已记录"),
    )
    library.save_active(messages)

    new_launcher, _new_service, new_library = _services(tmp_path)
    restored, restored_messages = new_library.activate(world.instance_id)

    assert restored_messages == messages
    assert restored.executor.character_minds[character_id] == mind
    assert restored.knowledge_retriever.snapshot()[0][0].id == "fact-known"
    assert restored.knowledge_retriever.snapshot()[1][0] == record
    assert restored.agent_context.character_id == session.agent_context.character_id
    assert new_launcher.current_session is restored


def test_world_patch_round_trip(tmp_path):
    launcher, _service, library = _services(tmp_path)
    session = _new_session(launcher)
    world = library.register(session)
    patch = WorldPatch(
        "patch-merchant", WorldPatchType.LORE_PATCH, "流浪商人记录", "补充一个传闻地点",
        "day-2", "day-3", "player", "旧车站附近偶尔有商人经过",
    )
    character_patch = WorldPatch(
        "patch-traveler",
        WorldPatchType.CHARACTER_ADDITION,
        "旅行商人加入",
        "从当前时间点加入一名旅行商人",
        "day-2",
        "day-3",
        "player",
        CharacterAddition(
            CharacterCard("traveler", "旅行商人", occupation="商人"),
            "收到无线电求助后抵达",
            "第二天清晨",
            "旅行商人抵达旧车站",
        ),
    )
    library.append_patch(world.instance_id, patch)
    library.append_patch(world.instance_id, character_patch)

    _launcher2, _service2, restarted = _services(tmp_path)
    restarted.activate(world.instance_id)

    assert restarted.patches_for(world.instance_id) == (patch, character_patch)


def test_corrupt_save_is_reported_without_deleting_other_worlds(tmp_path, qapp):
    launcher, service, library = _services(tmp_path)
    intact = library.register(_new_session(launcher))
    damaged = library.register(_new_session(launcher))
    save_path = tmp_path / "world_saves" / f"{damaged.instance_id}.json"
    save_path.write_text("{ not valid json", encoding="utf-8")

    listed = service.list_worlds()

    assert [item.instance_id for item in listed] == [intact.instance_id]
    assert damaged.instance_id in service.errors
    assert save_path.exists()
    with pytest.raises(WorldSaveError, match="无法读取"):
        service.load_world(damaged.instance_id)
    assert (tmp_path / "world_saves" / f"{intact.instance_id}.json").exists()
    from cognitive_sandbox.presentation.world_lobby import WorldLobbyPanel

    restarted_library = WorldLibrary(service, launcher.restore_saved_world)
    panel = WorldLobbyPanel(restarted_library)
    assert any(item.data(Qt.ItemDataRole.UserRole) == intact.instance_id for item in (
        panel.world_list.item(index) for index in range(panel.world_list.count())
    ))
    assert not panel.persistence_errors.isHidden()
    assert damaged.instance_id in panel.persistence_errors.text()
    panel.close()


def test_world_lobby_lists_persisted_saves_after_restart(tmp_path, qapp):
    launcher, _service, library = _services(tmp_path)
    session = _new_session(launcher, "example_world")
    saved = library.register(session)
    library.save_active((DisplayMessage("system", "已保存记录"),))

    _launcher2, _service2, restarted = _services(tmp_path)
    from cognitive_sandbox.presentation.world_lobby import WorldLobbyPanel

    panel = WorldLobbyPanel(restarted)
    assert panel.world_list.count() == 1
    assert saved.name in panel.world_list.item(0).text()
    assert saved.description in panel.world_list.item(0).text()
    assert "最近游玩：" in panel.world_list.item(0).text()
    assert panel.selected_world_id == saved.instance_id
    panel.close()


def test_save_serializer_never_persists_credentials(tmp_path):
    launcher, service, library = _services(tmp_path)
    session = _new_session(launcher)
    session.world_state["api_key"] = "must-not-be-written"
    world = library.register(session)

    # A failed save leaves the in-memory session alive and does not create a file.
    assert library.active_session() is session
    path = tmp_path / "world_saves" / f"{world.instance_id}.json"
    assert not path.exists()
    assert world.instance_id in library.persistence_errors
