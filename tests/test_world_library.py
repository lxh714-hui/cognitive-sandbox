from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QApplication, QDialog, QPushButton

from cognitive_sandbox.application.game_launcher import GameLauncher
from cognitive_sandbox.application.player_action_parser import PlayerActionParser
from cognitive_sandbox.presentation.main_window import FoundationMainWindow
from cognitive_sandbox.presentation.message import MessageType
from cognitive_sandbox.presentation.world_lobby import WorldLobbyPanel


@pytest.fixture
def qapp():
    return QApplication.instance() or QApplication([])


def test_creating_second_world_instance_does_not_change_first_world(qapp):
    window = FoundationMainWindow()
    launcher = GameLauncher(action_interpreter=PlayerActionParser())
    window.set_game_launcher(launcher)
    first_session = window.start_new_game("example_world")
    first_instance_id = window.current_world_instance_id
    first_session.world_state["information_level"] = 0.4
    window.append_player_message("第一世界的记录")

    second_session = window.start_new_game("example_world")
    second_instance_id = window.current_world_instance_id

    assert first_instance_id != second_instance_id
    assert first_session is not second_session
    assert first_session.world_instance_id != second_session.world_instance_id
    assert first_session.world_state["information_level"] == pytest.approx(0.4)
    assert "information_level" not in second_session.world_state
    assert len(window.world_library.list_worlds()) == 2
    window.close()


def test_startup_has_no_world_until_the_user_selects_or_creates_one(qapp):
    window = FoundationMainWindow()
    launcher = GameLauncher(action_interpreter=PlayerActionParser())
    window.set_game_launcher(launcher)

    assert window.current_session is None
    assert launcher.current_session is None
    assert window.world_library.list_worlds() == ()

    # Opening the startup lobby itself must not register a world.
    def close_startup_lobby() -> None:
        dialog = qapp.activeModalWidget()
        assert isinstance(dialog, QDialog)
        assert dialog.windowTitle() == "世界大厅"
        dialog.accept()

    QTimer.singleShot(0, close_startup_lobby)
    window.open_world_lobby()
    assert window.current_session is None
    assert window.world_library.list_worlds() == ()
    window.close()


def test_lobby_create_starts_new_world_flow_without_copying_a_scenario(qapp, monkeypatch):
    window = FoundationMainWindow()
    window.set_game_launcher(GameLauncher(action_interpreter=PlayerActionParser()))
    opened = []
    monkeypatch.setattr(window, "open_ai_world_creation", lambda: opened.append("new_world"))
    monkeypatch.setattr(window, "open_scenario_selection", lambda: opened.append("scenario_list"))

    def click_create() -> None:
        dialog = qapp.activeModalWidget()
        assert isinstance(dialog, QDialog)
        assert dialog.windowTitle() == "世界大厅"
        button = dialog.findChild(QPushButton, "createNewWorldButton")
        assert button is not None
        button.click()

    QTimer.singleShot(0, click_create)
    window.open_world_lobby()
    qapp.processEvents()

    assert opened == ["new_world"]
    assert window.world_library.list_worlds() == ()
    assert window.current_session is None
    window.close()


def test_switching_world_restores_runtime_state_and_its_own_chat_history(qapp):
    window = FoundationMainWindow()
    window.set_game_launcher(GameLauncher(action_interpreter=PlayerActionParser()))
    first_session = window.start_new_game("example_world")
    first_id = window.current_world_instance_id
    first_session.world_state["information_level"] = 0.7
    window.append_player_message("只属于灰港世界")
    first_messages = tuple(window.message_history)

    window.start_new_game("post_apocalypse_city")
    second_id = window.current_world_instance_id
    window.append_player_message("只属于末日城市")
    second_messages = tuple(window.message_history)

    window.switch_world(first_id)
    assert window.current_session is first_session
    assert window.current_session.world_state["information_level"] == pytest.approx(0.7)
    assert tuple(window.message_history) == first_messages
    assert "只属于末日城市" not in window.narrative_display.toPlainText()

    window.switch_world(second_id)
    assert "只属于末日城市" in window.narrative_display.toPlainText()
    assert tuple(window.message_history) == second_messages
    assert "只属于灰港世界" not in window.narrative_display.toPlainText()
    window.close()


def test_lobby_selection_continues_existing_world(qapp):
    window = FoundationMainWindow()
    window.set_game_launcher(GameLauncher(action_interpreter=PlayerActionParser()))
    first_session = window.start_new_game("example_world")
    first_id = window.current_world_instance_id
    first_session.world_state["information_level"] = 0.8
    window.start_new_game("post_apocalypse_city")

    def continue_first_world() -> None:
        dialog = qapp.activeModalWidget()
        assert isinstance(dialog, QDialog)
        panel = dialog.findChild(WorldLobbyPanel)
        assert panel is not None
        item = next(
            panel.world_list.item(index)
            for index in range(panel.world_list.count())
            if panel.world_list.item(index).data(Qt.ItemDataRole.UserRole) == first_id
        )
        panel.world_list.setCurrentItem(item)
        panel.continue_button.click()

    QTimer.singleShot(0, continue_first_world)
    window.open_world_lobby()

    assert window.current_session is first_session
    assert window.current_session.world_state["information_level"] == pytest.approx(0.8)
    assert window.current_world_instance_id == first_id
    window.close()


def test_world_library_panel_shows_names_state_and_recent_play(qapp):
    window = FoundationMainWindow()
    window.set_game_launcher(GameLauncher(action_interpreter=PlayerActionParser()))
    window.start_new_game("example_world")
    window.start_new_game("post_apocalypse_city")

    panel = WorldLobbyPanel(window.world_library)
    assert panel.world_list.count() == 2
    labels = [panel.world_list.item(i).text() for i in range(panel.world_list.count())]
    assert any("灰港纪元" in label and "地点：" in label and "最近游玩：" in label for label in labels)
    assert any("末日城市" in label and "最近游玩：" in label for label in labels)
    assert panel.continue_button.isEnabled()
    assert panel.extend_button.isEnabled()
    panel.world_list.setCurrentRow(0)
    assert panel.selected_world_id is not None
    window.close()


def test_chat_history_records_have_world_local_message_order(qapp):
    window = FoundationMainWindow()
    window.set_game_launcher(GameLauncher(action_interpreter=PlayerActionParser()))
    window.start_new_game("post_apocalypse_city")
    instance_id = window.current_world_instance_id

    window.append_player_message("玩家行动")
    window.append_system_message("系统提示")
    saved = window.world_library.messages_for(instance_id)

    assert saved[-1].message_type is MessageType.PLAYER
    assert window.system_message_label.text() == "系统提示"
    window.close()
