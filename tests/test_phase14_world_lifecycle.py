import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMessageBox

from cognitive_sandbox.application.action_intent_parser import ActionIntentParser
from cognitive_sandbox.application.game_launcher import GameLauncher
from cognitive_sandbox.application.world_library import WorldLibrary
from cognitive_sandbox.application.world_manager import WorldLifecycleError, WorldManager
from cognitive_sandbox.domain.simulation_result import SimulationTickResult
from cognitive_sandbox.presentation.main_window import FoundationMainWindow


@pytest.fixture
def qapp():
    return QApplication.instance() or QApplication([])


def test_world_manager_deletes_inactive_instance_and_rejects_active_instance():
    launcher = GameLauncher()
    library = WorldLibrary()
    manager = WorldManager(library)
    first = launcher.start_scenario("example_world")
    first_item = library.register(first)
    second = launcher.start_scenario("post_apocalypse_city")
    second_item = library.register(second)

    assert manager.delete_world(first_item.instance_id) is True
    assert first_item.instance_id not in {item.instance_id for item in library.list_worlds()}
    with pytest.raises(WorldLifecycleError, match="正在运行"):
        manager.delete_world(second_item.instance_id)
    assert second_item.instance_id in {item.instance_id for item in library.list_worlds()}


def test_world_lobby_deletion_requires_confirmation_and_uses_world_manager(qapp, monkeypatch):
    window = FoundationMainWindow()
    window.set_game_launcher(GameLauncher())
    first = window.start_new_game("example_world")
    first_id = window.current_world_instance_id
    window.start_new_game("post_apocalypse_city")
    assert first_id != window.current_world_instance_id
    answers = []
    monkeypatch.setattr(
        QMessageBox, "question",
        lambda *_args, **_kwargs: answers.append(True) or QMessageBox.StandardButton.Yes,
    )

    from cognitive_sandbox.presentation.world_lobby import WorldLobbyPanel
    panel = WorldLobbyPanel(window.world_library)
    window._delete_world_from_lobby(first_id, panel)
    assert answers == [True]
    assert first_id not in {item.instance_id for item in window.world_library.list_worlds()}
    assert window.current_world_instance_id is not None
    window.close()


def test_mappingproxy_nested_state_can_be_snapshotted_after_an_action():
    launcher = GameLauncher()
    session = launcher.start_scenario("example_world")
    result = SimulationTickResult(
        {"nested": {"visible": ("灯光", "脚步声")}}, session.agent_context, ()
    )
    session.world_state = result.world_state
    library = WorldLibrary()
    library.register(session)
    library.save_active(())
    assert library._records[session.world_instance_id].snapshot[0] == {
        "nested": {"visible": ("灯光", "脚步声")}
    }


def test_playable_anchor_flow_guides_observes_and_talks_without_duplicate_echo(qapp):
    window = FoundationMainWindow()
    window.set_game_launcher(GameLauncher(action_interpreter=ActionIntentParser()))
    session = window.game_launcher.start_world("anchor")
    window._attach_roleplay_session(session)
    opening = window.narrative_display.toPlainText()
    assert "梁景" in opening
    assert "刑满释放" in opening
    assert "窗台" in opening
    assert "这里是《" not in opening

    initial_world = dict(session.world_state)
    window.ui_runtime.handle_player_input("我不知道该干什么")
    guidance = window.ui_runtime.execute_confirm()
    window.ui_runtime.present_result(guidance)
    assert "值得注意" not in window.system_message_label.text()
    assert "此刻没有必须完成的事" in window.narrative_display.toPlainText()
    assert dict(session.world_state) == initial_world

    window.ui_runtime.handle_player_input("我看看附近有什么")
    observation = window.ui_runtime.execute_confirm()
    window.ui_runtime.present_result(observation)
    transcript = window.narrative_display.toPlainText()
    assert "你环顾四周" not in transcript
    assert "梁景住所" in transcript
    assert window.message_history[-1].content != "正在生成..."

    window.ui_runtime.handle_player_input("和柳依依聊聊")
    conversation = window.ui_runtime.execute_confirm()
    window.ui_runtime.present_result(conversation)
    assert conversation.action_executed
    assert window.message_history[-1].speaker_id == "柳依依"
    assert all(item.content != "正在生成..." for item in window.message_history)

    # Trigger the actual application save boundary after immutable event state.
    window.world_library.save_active(window.message_history)
    assert window.current_world_instance_id in window.world_library._records
    window.close()
