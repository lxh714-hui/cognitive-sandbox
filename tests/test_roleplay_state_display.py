from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from cognitive_sandbox.application.game_launcher import GameLauncher
from cognitive_sandbox.presentation.main_window import FoundationMainWindow


def test_active_session_header_shows_world_character_location_and_day():
    app = QApplication.instance() or QApplication([])
    window = FoundationMainWindow()
    launcher = GameLauncher()
    window.set_game_launcher(launcher)
    session = launcher.start_anchor_world()
    window._attach_roleplay_session(session)

    text = window.world_context_label.text()
    assert "《锚点》" in text
    assert "梁景" in text
    assert "梁景住所" in text
    assert "Day 1" in text
    assert "未进入世界" not in text
    window.close()


def test_missing_session_alone_shows_outside_world_state():
    app = QApplication.instance() or QApplication([])
    window = FoundationMainWindow()
    window._refresh_world_context()
    assert window.world_context_label.text() == "未进入世界"
    window.close()

