from __future__ import annotations

import os
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication


def _wait_idle(app, window, timeout=3):
    deadline = time.monotonic() + timeout
    while window._is_processing and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.005)
    app.processEvents()
    assert not window._is_processing

from cognitive_sandbox.application.game_launcher import GameLauncher
from cognitive_sandbox.application.player_action_parser import PlayerActionParser
from cognitive_sandbox.domain.narrative_event import NarrativeEvent
from cognitive_sandbox.presentation.main_window import FoundationMainWindow
from cognitive_sandbox.presentation.message import MessageType


@pytest.fixture
def qapp():
    return QApplication.instance() or QApplication([])


def _start_example(window):
    launcher = GameLauncher(action_interpreter=PlayerActionParser())
    window.set_game_launcher(launcher)
    session = window.start_new_game("example_world")
    return launcher, session


def test_scenario_start_shows_natural_opening_without_internal_status_dump(qapp):
    window = FoundationMainWindow()
    _launcher, _session = _start_example(window)

    opening = window.message_history[0]
    assert opening.message_type is MessageType.NARRATION
    assert opening.speaker_id is None
    assert "灰港纪元" in opening.content
    assert "灾难后的海港城市" in opening.content
    assert "港区旧诊所大厅" in opening.content
    assert "你是玩家" not in opening.content
    assert "幸存者" in opening.content
    assert "沈医生" in opening.content
    assert "周岚" not in opening.content
    assert "20%" not in opening.content
    assert "energy_level" not in opening.content
    assert "城市备用能源即将耗尽" in opening.content
    window.close()


def test_legacy_scenario_without_opening_content_uses_safe_fallback(qapp):
    window = FoundationMainWindow()
    launcher = GameLauncher(action_interpreter=PlayerActionParser())
    window.set_game_launcher(launcher)
    window.start_new_game("post_apocalypse_city")

    opening = window.message_history[0].content
    assert "一座在灾后艰难维持生活的城市" in opening
    assert "灾后艰难维持生活的城市" in opening
    assert "当前地点尚未设定" not in opening
    assert "士兵、幸存者" not in opening
    assert "doctor" not in opening
    window.close()


def test_transcript_resolves_character_ids_to_names_or_omits_them(qapp):
    window = FoundationMainWindow()
    _launcher, _session = _start_example(window)
    window.append_narrative_event(NarrativeEvent("event-x", "相遇", "有人出现了", ("doctor", "unknown-id")))
    text = window.narrative_display.toPlainText()

    assert "沈医生" in text
    assert "doctor" not in text
    assert "unknown-id" not in text
    window.close()


def test_observe_action_shows_readable_scenario_feedback(qapp):
    window = FoundationMainWindow()
    _launcher, _session = _start_example(window)

    window.player_input.setPlainText("观察周围环境")
    window.confirm_button.click()
    _wait_idle(qapp, window)
    text = window.narrative_display.toPlainText()

    assert "观察周围环境" in text
    assert "你环顾四周" not in text
    assert "港区旧诊所大厅" in text
    assert "城市备用能源即将耗尽" in text
    assert "%" not in text
    assert "沈医生" in text
    assert "doctor" not in text
    assert "information_level" not in text
    assert "开始观察" not in text
    assert "角色开始留意周围环境" not in text
    window.close()


def test_player_world_system_message_order_remains_intuitive(qapp):
    window = FoundationMainWindow()
    launcher = GameLauncher(action_interpreter=PlayerActionParser())
    window.set_game_launcher(launcher)
    window.start_new_game("post_apocalypse_city")
    window.player_input.setPlainText("帮助医生")
    window.confirm_button.click()
    _wait_idle(qapp, window)
    window.append_system_message("本轮提示")

    history = window.message_history
    player_index = next(i for i, item in enumerate(history) if item.message_type is MessageType.PLAYER)
    character_index = next(
        i for i, item in enumerate(history[player_index + 1:], player_index + 1)
        if item.message_type is MessageType.CHARACTER
    )
    assert player_index < character_index
    assert window.system_message_label.text() == "本轮提示"
    assert all(item.message_type not in {MessageType.SYSTEM, MessageType.SYSTEM_ERROR, MessageType.SYSTEM_TEMP}
               for item in history)
    window.close()
