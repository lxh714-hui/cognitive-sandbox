import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from cognitive_sandbox.application.game_launcher import GameLauncher
from cognitive_sandbox.presentation.main_window import FoundationMainWindow


@pytest.fixture
def qapp():
    return QApplication.instance() or QApplication([])


def test_director_mode_shows_panel_and_quick_action_creates_soft_goal(qapp):
    window = FoundationMainWindow()
    launcher = GameLauncher()
    window.set_game_launcher(launcher)
    session = window.start_new_game("example_world")
    window.set_mode("director")
    assert not window.director_panel.isHidden()
    assert window.director_panel.submit_button.isEnabled()
    result = window.director_panel.submit_quick(
        window.director_panel.QUICK_OPTIONS[0][1], "促进角色相遇"
    )
    assert result.accepted
    assert session.director_history[-1] == result
    window.set_mode("roleplay")
    assert window.director_panel.isHidden()
    window.close()
