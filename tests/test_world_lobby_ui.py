import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from cognitive_sandbox.presentation.world_lobby import WorldLobbyPanel


def test_lobby_has_world_card_list_and_all_mode_entry_buttons():
    app = QApplication.instance() or QApplication([])
    class Library:
        persistence_errors = {}
        def list_worlds(self): return ()
    from cognitive_sandbox.application.scenario_loader import ScenarioLoader
    panel = WorldLobbyPanel(Library(), ScenarioLoader().registry)
    assert panel.world_list.count() == 0
    assert panel.scenario_list.count() > 0
    assert panel.start_scenario_button.text() == "创建世界实例"
    panel.close()
