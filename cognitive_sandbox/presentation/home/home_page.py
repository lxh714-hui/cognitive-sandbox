from PySide6.QtCore import Signal
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton, QVBoxLayout

from .mode_selector import ModeSelector
from .world_card_widget import WorldCardWidget


class HomePage(QDialog):
    enter_world = Signal(str)
    create_world = Signal()
    observe_simulation = Signal()
    director_mode = Signal()
    debug_requested = Signal()

    def __init__(self, world_library=None, parent=None):
        super().__init__(parent)
        self.world_library = world_library
        self.setObjectName("homePage")
        self.setWindowTitle("Cognitive Sandbox")
        self.resize(720, 560)
        layout = QVBoxLayout(self)
        title = QLabel("Cognitive Sandbox", self)
        title.setObjectName("homeTitle")
        subtitle = QLabel("一个会产生故事的世界模拟沙盒", self)
        subtitle.setObjectName("homeSubtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(QLabel("最近世界 / 最近存档", self))
        self.recent_worlds = QListWidget(self)
        self.recent_worlds.setObjectName("homeRecentWorlds")
        layout.addWidget(self.recent_worlds, 1)
        self.simulation_status = QLabel("模拟状态：选择一个世界开始", self)
        self.simulation_status.setObjectName("homeSimulationStatus")
        layout.addWidget(self.simulation_status)
        self.mode_selector = ModeSelector(self)
        layout.addWidget(self.mode_selector)
        row = QHBoxLayout()
        for label, name, handler in (("进入世界", "enterWorldButton", self._enter),
                                     ("创建世界", "createWorldButton", self._create),
                                     ("观察模拟", "observeSimulationButton", self._observe),
                                     ("导演模式", "directorModeButton", self._director)):
            button = QPushButton(label, self)
            button.setObjectName(name)
            button.clicked.connect(handler)
            row.addWidget(button)
            setattr(self, name, button)
        self.developer_button = QPushButton("开发者诊断", self)
        self.developer_button.setObjectName("developerModeButton")
        self.developer_button.clicked.connect(self.debug_requested.emit)
        row.addWidget(self.developer_button)
        layout.addLayout(row)
        self.refresh()

    def refresh(self):
        self.recent_worlds.clear()
        if self.world_library is None:
            return
        for world in self.world_library.list_worlds()[:5]:
            details = getattr(self.world_library, "summary_for", lambda _id: {})(world.instance_id)
            status = f"{world.world_status} · 最近游玩 {world.last_played}"
            card = WorldCardWidget(world.name, world.description, status)
            item = QListWidgetItem(self.recent_worlds)
            item.setSizeHint(card.sizeHint())
            self.recent_worlds.addItem(item)
            self.recent_worlds.setItemWidget(item, card)
            day = details.get("day")
            current = f"Day {day}" if day is not None else status
            card.status_label.setText(
                f"版本 {details.get('version', '未标注')} · 角色 {details.get('character_count', '—')} · "
                f"{current}"
            )

    def _enter(self):
        self.enter_world.emit(str(self.mode_selector.currentData()))

    def _create(self):
        self.create_world.emit()

    def _observe(self):
        self.observe_simulation.emit()

    def _director(self):
        self.director_mode.emit()
