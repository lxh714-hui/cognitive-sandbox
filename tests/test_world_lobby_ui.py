import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from cognitive_sandbox.presentation.world_lobby import WorldLobbyPanel


def test_lobby_has_world_card_list_and_all_mode_entry_buttons():
    app = QApplication.instance() or QApplication([])
    class Library:
        persistence_errors = {}
        def list_worlds(self): return ()
    panel = WorldLobbyPanel(Library())
    assert panel.world_list.count() == 0
    assert panel.anchor_button.text() == "进入《锚点》"
    assert panel.anchor_simulation_button.text() == "观察《锚点》"
    panel.close()
