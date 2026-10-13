from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton, QVBoxLayout, QWidget


class WorldLobbyPanel(QWidget):
    """World library chooser with continue and create-new entry points."""

    continue_requested = Signal(str)
    scenario_requested = Signal(str)
    create_requested = Signal()
    extend_requested = Signal(str)
    delete_requested = Signal(str)

    def __init__(self, world_library, scenario_registry=None, parent=None) -> None:
        super().__init__(parent)
        self.world_library = world_library
        self.scenario_registry = scenario_registry
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("继续已有世界，或创建一个新的世界实例。", self))
        self.persistence_errors = QLabel(self)
        self.persistence_errors.setObjectName("worldSaveErrors")
        self.persistence_errors.setWordWrap(True)
        layout.addWidget(self.persistence_errors)
        self.world_list = QListWidget(self)
        self.world_list.setObjectName("worldLibraryList")
        layout.addWidget(self.world_list)
        layout.addWidget(QLabel("可用世界包", self))
        self.scenario_list = QListWidget(self)
        self.scenario_list.setObjectName("scenarioPackageList")
        layout.addWidget(self.scenario_list)
        buttons = QHBoxLayout()
        self.continue_button = QPushButton("继续已有世界", self)
        self.continue_button.setObjectName("continueWorldButton")
        self.create_button = QPushButton("创建新世界", self)
        self.create_button.setObjectName("createNewWorldButton")
        self.extend_button = QPushButton("扩展世界", self)
        self.extend_button.setObjectName("extendWorldButton")
        self.delete_button = QPushButton("删除世界", self)
        self.delete_button.setObjectName("deleteWorldButton")
        self.start_scenario_button = QPushButton("创建世界实例", self)
        self.start_scenario_button.setObjectName("startScenarioPackageButton")
        buttons.addWidget(self.continue_button)
        buttons.addWidget(self.create_button)
        buttons.addWidget(self.extend_button)
        buttons.addWidget(self.delete_button)
        buttons.addWidget(self.start_scenario_button)
        layout.addLayout(buttons)
        self.continue_button.clicked.connect(self._continue_selected)
        self.create_button.clicked.connect(self.create_requested.emit)
        self.extend_button.clicked.connect(self._extend_selected)
        self.delete_button.clicked.connect(self._delete_selected)
        self.start_scenario_button.clicked.connect(self._start_selected_scenario)
        self.world_list.currentItemChanged.connect(self._selection_changed)
        self.scenario_list.currentItemChanged.connect(self._scenario_selection_changed)
        self.refresh()

    @property
    def selected_world_id(self) -> str | None:
        item = self.world_list.currentItem()
        return str(item.data(Qt.ItemDataRole.UserRole)) if item is not None else None

    @property
    def selected_scenario_id(self) -> str | None:
        item = self.scenario_list.currentItem()
        return str(item.data(Qt.ItemDataRole.UserRole)) if item is not None else None

    def refresh(self) -> None:
        self.world_list.clear()
        current_item = None
        for world in self.world_library.list_worlds():
            details = getattr(self.world_library, "summary_for", lambda _id: {})(world.instance_id)
            version = details.get("version", "版本信息待提供")
            count = details.get("character_count", "—")
            day = details.get("day")
            recent = details.get("recent_summary", world.world_status)
            status = f"{world.status} · {f'Day {day}' if day is not None else world.world_status}"
            item = QListWidgetItem(
                f"{world.name}\n{world.description}\n版本：{version} · 角色：{count}\n{status}\n"
                f"最近动态：{recent}\n最近游玩：{world.last_played}"
            )
            item.setData(Qt.ItemDataRole.UserRole, world.instance_id)
            item.setToolTip(f"{world.name} · {world.world_status} · {world.last_played}")
            self.world_list.addItem(item)
            if world.status == "当前世界":
                current_item = item
        if current_item is not None:
            self.world_list.setCurrentItem(current_item)
        elif self.world_list.count():
            self.world_list.setCurrentRow(0)
        self.continue_button.setEnabled(self.selected_world_id is not None)
        self.extend_button.setEnabled(self.selected_world_id is not None)
        self.delete_button.setEnabled(
            self.selected_world_id is not None
            and self.selected_world_id != getattr(self.world_library, "active_id", None)
        )
        self.scenario_list.clear()
        scenarios = self.scenario_registry.list_available() if self.scenario_registry is not None else ()
        for scenario in scenarios:
            item = QListWidgetItem(f"{scenario.name}\n{scenario.description}")
            item.setData(Qt.ItemDataRole.UserRole, scenario.scenario_id)
            self.scenario_list.addItem(item)
        if self.scenario_list.count():
            self.scenario_list.setCurrentRow(0)
        self.start_scenario_button.setEnabled(self.selected_scenario_id is not None)
        errors = getattr(self.world_library, "persistence_errors", {})
        if errors:
            self.persistence_errors.setText("部分世界存档无法读取：\n" + "\n".join(errors.values()))
            self.persistence_errors.show()
        else:
            self.persistence_errors.clear()
            self.persistence_errors.hide()

    def _selection_changed(self, _current, _previous) -> None:
        self.continue_button.setEnabled(self.selected_world_id is not None)
        self.extend_button.setEnabled(self.selected_world_id is not None)
        self.delete_button.setEnabled(
            self.selected_world_id is not None
            and self.selected_world_id != getattr(self.world_library, "active_id", None)
        )

    def _scenario_selection_changed(self, _current, _previous) -> None:
        self.start_scenario_button.setEnabled(self.selected_scenario_id is not None)

    def _start_selected_scenario(self) -> None:
        scenario_id = self.selected_scenario_id
        if scenario_id is not None:
            self.scenario_requested.emit(scenario_id)

    def _continue_selected(self) -> None:
        instance_id = self.selected_world_id
        if instance_id is not None:
            self.continue_requested.emit(instance_id)

    def _extend_selected(self) -> None:
        instance_id = self.selected_world_id
        if instance_id is not None:
            self.extend_requested.emit(instance_id)

    def _delete_selected(self) -> None:
        instance_id = self.selected_world_id
        if instance_id is not None and instance_id != getattr(self.world_library, "active_id", None):
            self.delete_requested.emit(instance_id)
