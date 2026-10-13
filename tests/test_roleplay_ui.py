import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from cognitive_sandbox.presentation.roleplay import RoleplayView
from PySide6.QtWidgets import QApplication


def test_roleplay_view_composes_player_facing_panels():
    app = QApplication.instance() or QApplication([])
    view = RoleplayView()
    assert view.time_location.objectName() == "roleplayTimeLocation"
    assert view.dialogue_panel.history.objectName() == "roleplayDialogueHistory"
    assert view.action_panel.objectName() != ""
    view.close()
