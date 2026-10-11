from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLabel, QListWidget, QListWidgetItem, QPushButton, QVBoxLayout, QWidget

from cognitive_sandbox.application.scenario_registry import ScenarioRegistry


class ScenarioSelectionPanel(QWidget):
    """Display registered scenarios and emit the selected ID on start."""

    scenario_started = Signal(str)

    def __init__(self, registry: ScenarioRegistry, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        if not isinstance(registry, ScenarioRegistry):
            raise TypeError("registry must be a ScenarioRegistry.")
        self.registry = registry

        layout = QVBoxLayout(self)
        self.scenario_list = QListWidget(self)
        self.scenario_list.setObjectName("scenarioList")
        self.description = QLabel(self)
        self.description.setObjectName("scenarioDescription")
        self.description.setWordWrap(True)
        self.start_button = QPushButton("开始", self)
        self.start_button.setObjectName("startScenarioButton")
        layout.addWidget(self.scenario_list)
        layout.addWidget(self.description)
        layout.addWidget(self.start_button)

        for scenario in self.registry.list_available():
            item = QListWidgetItem(scenario.name)
            item.setData(Qt.ItemDataRole.UserRole, scenario.scenario_id)
            self.scenario_list.addItem(item)

        self.scenario_list.currentItemChanged.connect(self._update_description)
        self.start_button.clicked.connect(self._emit_selected_scenario)
        self.start_button.setEnabled(self.scenario_list.count() > 0)
        if self.scenario_list.count():
            self.scenario_list.setCurrentRow(0)

    @property
    def selected_scenario_id(self) -> str | None:
        item = self.scenario_list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item is not None else None

    def start_selected(self) -> str | None:
        """Return the selected scenario ID, or None when nothing is selected."""
        return self.selected_scenario_id

    def _update_description(self, current: QListWidgetItem | None, _previous) -> None:
        scenario_id = current.data(Qt.ItemDataRole.UserRole) if current is not None else None
        scenario = self.registry.get(scenario_id) if scenario_id else None
        self.description.setText(scenario.description if scenario is not None else "")
        self.start_button.setEnabled(scenario is not None)

    def _emit_selected_scenario(self) -> None:
        scenario_id = self.start_selected()
        if scenario_id is not None:
            self.scenario_started.emit(scenario_id)
