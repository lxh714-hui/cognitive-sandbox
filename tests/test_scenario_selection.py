from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from cognitive_sandbox.application.scenario_loader import ScenarioLoader
from cognitive_sandbox.application.scenario_registry import ScenarioRegistry
from cognitive_sandbox.application.game_launcher import GameLauncher
from cognitive_sandbox.presentation.main_window import FoundationMainWindow
from cognitive_sandbox.presentation.scenario_selection import ScenarioSelectionPanel


@pytest.fixture
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_panel_lists_registered_scenarios_and_descriptions(qapp):
    registry = ScenarioLoader().registry
    panel = ScenarioSelectionPanel(registry)

    available = {panel.scenario_list.item(i).data(Qt.ItemDataRole.UserRole)
                 for i in range(panel.scenario_list.count())}
    assert available == {scenario.scenario_id for scenario in registry.list_available()}
    assert panel.scenario_list.count() == len(registry.list_available())
    assert panel.start_button.isEnabled()
    panel.close()


def test_selecting_and_starting_returns_scenario_id(qapp):
    registry = ScenarioLoader().registry
    panel = ScenarioSelectionPanel(registry)
    started: list[str] = []
    panel.scenario_started.connect(started.append)

    scenario_id = panel.scenario_list.item(panel.scenario_list.count() - 1).data(Qt.ItemDataRole.UserRole)
    index = next(i for i in range(panel.scenario_list.count())
                 if panel.scenario_list.item(i).data(Qt.ItemDataRole.UserRole) == scenario_id)
    panel.scenario_list.setCurrentRow(index)
    scenario_id = panel.start_selected()
    panel.start_button.click()

    assert scenario_id in {scenario.scenario_id for scenario in registry.list_available()}
    assert started == [scenario_id]
    panel.close()


def test_empty_registry_has_no_startable_scenario(qapp):
    panel = ScenarioSelectionPanel(ScenarioRegistry())

    assert panel.selected_scenario_id is None
    assert panel.start_selected() is None
    assert not panel.start_button.isEnabled()
    panel.close()


def test_main_window_starts_selected_scenario_session(qapp):
    window = FoundationMainWindow()
    launcher = GameLauncher()
    window.set_game_launcher(launcher)

    session = window.start_new_game("post_apocalypse_city")

    assert window.current_session is session
    assert window.ui_runtime.session is session
    assert session.current_turn.status == "waiting_input"
    assert window.player_input.isEnabled()
    window.close()
