import os
import pytest
from PySide6.QtWidgets import QApplication

from cognitive_sandbox.application.game_launcher import GameLauncher
from cognitive_sandbox.presentation.story_mode.story_view import StoryView


@pytest.fixture
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    return QApplication.instance() or QApplication([])


def test_story_mode_shows_player_facing_world_and_can_advance(qapp):
    session = GameLauncher().start_world("anchor")
    view = StoryView(session)
    before = session.executor.world_clock.current_time()
    assert "锚点" in view.title.text()
    assert "模拟诊断" not in view.timeline.replay.view.toPlainText()
    assert "以梁景身份行动" in view.player_choice.text()
    rows = view.advance_day()
    after = session.executor.world_clock.current_time()
    assert (after - before).days == 1
    assert isinstance(rows, tuple)
