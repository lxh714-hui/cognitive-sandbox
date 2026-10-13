from __future__ import annotations

import logging
from datetime import datetime

from PySide6.QtCore import QObject, QSettings, QTimer, Qt, QThread, Signal, Slot
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QButtonGroup, QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget, QMainWindow, QSplitter, QSplitterHandle,
    QPushButton, QSizePolicy, QTextBrowser, QVBoxLayout, QWidget, QMenu, QInputDialog,
)

from cognitive_sandbox.application.service import SandboxService
from cognitive_sandbox.application.world_library import WorldLibrary
from cognitive_sandbox.application.world_manager import WorldManager, WorldLifecycleError
from cognitive_sandbox.domain.models import Agent, CognitiveMemory, ConversationEvent, World
from cognitive_sandbox.domain.runtime_mode import RuntimeMode
from cognitive_sandbox.infrastructure.static_sprites import StaticSpriteRenderer
from cognitive_sandbox.presentation.message import DisplayMessage, MessageType
from cognitive_sandbox.presentation.scenario_presenter import ScenarioPresenter


logger = logging.getLogger(__name__)


class TurnWorker(QObject):
    finished = Signal(str)
    failed = Signal(str)

    def __init__(self, service: SandboxService, world: World, agent: Agent, prompt: str) -> None:
        super().__init__()
        self.service, self.world, self.agent, self.prompt = service, world, agent, prompt

    @Slot()
    def run(self) -> None:
        try:
            reply = self.service.generate_reply(self.world, self.agent, self.prompt)
            self.service.record_agent_reply(self.world, self.agent, reply)
            self.finished.emit(reply)
        except Exception as exc:
            self.failed.emit(str(exc))


class SidebarHandle(QWidget):
    """Small toggle positioned over the splitter's fixed divider."""

    def __init__(self, window: "MainWindow") -> None:
        super().__init__(window)
        self.setObjectName("sidebarHandle")
        self.setFixedSize(30, 30)
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._button = QPushButton("▶", self)
        self._button.setObjectName("sidebarHandleButton")
        self._button.setFixedSize(28, 28)
        self._button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._button.clicked.connect(window.toggle_sidebar)
        self._button.move(1, 1)


class FixedSplitterHandle(QSplitterHandle):
    def mousePressEvent(self, event) -> None:  # noqa: N802 - Qt API name
        event.accept()

    def mouseMoveEvent(self, event) -> None:  # noqa: N802 - Qt API name
        event.accept()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802 - Qt API name
        event.accept()


class FixedSplitter(QSplitter):
    """Keep the visual divider while preventing pointer based resizing."""

    def createHandle(self) -> QSplitterHandle:  # noqa: N802 - Qt API name
        handle = FixedSplitterHandle(self.orientation(), self)
        handle.setCursor(Qt.CursorShape.ArrowCursor)
        return handle


class MainWindow(QMainWindow):
    def __init__(self, service: SandboxService, world: World, agent: Agent,
                 memories: tuple[CognitiveMemory, ...], renderer: StaticSpriteRenderer) -> None:
        super().__init__()
        self.service, self.world, self.agent, self.renderer = service, world, agent, renderer
        self._thread: QThread | None = None
        self._worker: TurnWorker | None = None
        self.setWindowTitle("Cognitive Sandbox")
        self.resize(1180, 760)
        self.setMinimumSize(520, 420)
        self._settings = QSettings("CognitiveSandbox", "CognitiveSandbox")
        self._settings.remove("sidebar/width")
        self._inspector_collapsed = False
        self._build_ui(memories)
        self._load_history()

    def _build_ui(self, memories: tuple[CognitiveMemory, ...]) -> None:
        root = QWidget()
        root.setObjectName("root")
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(16, 16, 16, 16)
        root_layout.setSpacing(0)

        left = QFrame()
        left.setObjectName("sceneCard")
        left.setMinimumWidth(0)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(18, 15, 18, 18)
        header = QHBoxLayout()
        brand = QLabel("COGNITIVE SANDBOX")
        brand.setObjectName("eyebrow")
        scene = QLabel(self.world.name)
        scene.setObjectName("worldName")
        header.addWidget(brand)
        header.addStretch()
        header.addWidget(scene)
        left_layout.addLayout(header)

        mode_row = QHBoxLayout()
        mode_row.setSpacing(8)
        self.roleplay_mode_button = QPushButton("人物扮演")
        self.roleplay_mode_button.setObjectName("modeButton")
        self.roleplay_mode_button.setCheckable(True)
        self.roleplay_mode_button.setAccessibleName("切换到人物扮演模式")
        self.story_mode_button = QPushButton("剧情推演")
        self.story_mode_button.setObjectName("modeButton")
        self.story_mode_button.setCheckable(True)
        self.story_mode_button.setAccessibleName("切换到剧情推演模式")
        self._mode_buttons = (self.roleplay_mode_button, self.story_mode_button)
        self.mode_button_group = QButtonGroup(self)
        self.mode_button_group.setExclusive(True)
        self.mode_button_group.addButton(self.roleplay_mode_button)
        self.mode_button_group.addButton(self.story_mode_button)
        self.roleplay_mode_button.clicked.connect(lambda: self._set_runtime_mode(RuntimeMode.ROLEPLAY))
        self.story_mode_button.clicked.connect(lambda: self._set_runtime_mode(RuntimeMode.STORY_SIMULATION))
        self.mode_status = QLabel()
        self.mode_status.setObjectName("modeStatus")
        mode_row.addWidget(self.roleplay_mode_button)
        mode_row.addWidget(self.story_mode_button)
        mode_row.addWidget(self.mode_status, 1)
        left_layout.addLayout(mode_row)
        stage = QFrame()
        stage.setObjectName("stage")
        stage.setMinimumHeight(310)
        stage_layout = QVBoxLayout(stage)
        stage_layout.setContentsMargins(0, 0, 0, 0)
        stage_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom)
        self.sprite = QLabel()
        self.sprite.setAlignment(Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter)
        self.sprite.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        stage_layout.addWidget(self.sprite)
        self._refresh_sprite()
        left_layout.addWidget(stage, 3)

        dialogue = QFrame()
        dialogue.setObjectName("dialogue")
        dialogue_layout = QVBoxLayout(dialogue)
        dialogue_layout.setContentsMargins(20, 15, 20, 15)
        name = QLabel(self.agent.name)
        name.setObjectName("speaker")
        self.transcript = QTextBrowser()
        self.transcript.setObjectName("transcript")
        self.transcript.setOpenExternalLinks(False)
        self.transcript.setMinimumHeight(145)
        self.transcript.setMaximumHeight(220)
        dialogue_layout.addWidget(name)
        dialogue_layout.addWidget(self.transcript)
        left_layout.addWidget(dialogue, 2)

        input_row = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setObjectName("input")
        self.input.setPlaceholderText("描述你的行动或想说的话……")
        self.input.returnPressed.connect(self._submit)
        self.send_button = QPushButton("发送  ↗")
        self.send_button.setObjectName("sendButton")
        self.send_button.clicked.connect(self._submit)
        self.input.textChanged.connect(self._update_send_button)
        self._update_send_button(self.input.text())
        input_row.addWidget(self.input, 1)
        input_row.addWidget(self.send_button)
        left_layout.addLayout(input_row)
        self._set_runtime_mode(RuntimeMode.ROLEPLAY)
        self.status = QLabel(f"{self.service.provider.label}  ·  对话保存在本地")
        self.status.setObjectName("status")
        left_layout.addWidget(self.status)

        panel = QFrame()
        panel.setObjectName("inspector")
        panel.setMinimumWidth(160)
        panel.setMaximumWidth(560)
        panel.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(18, 18, 18, 18)
        panel_layout.setSpacing(12)
        panel_title = QLabel("世界档案")
        panel_title.setObjectName("panelTitle")
        panel_layout.addWidget(panel_title)
        panel_layout.addWidget(self._section("当前世界", self.world.name, self.world.description))
        facts = "\n".join(f"•  {fact}" for fact in self.world.facts)
        panel_layout.addWidget(self._section("世界状态", "", facts))
        panel_layout.addWidget(self._section("角色档案", f"{self.agent.name}  /  {self.agent.role}", self.agent.persona))

        memory_title = QLabel("认知记忆")
        memory_title.setObjectName("sectionTitle")
        panel_layout.addWidget(memory_title)
        memory_list = QListWidget()
        memory_list.setObjectName("memoryList")
        for memory in memories:
            memory_list.addItem(memory.note)
        memory_list.setFixedHeight(105)
        panel_layout.addWidget(memory_list)
        panel_layout.addStretch()
        footer = QLabel("LOCAL SANDBOX  ·  MVP 0.1")
        footer.setObjectName("status")
        panel_layout.addWidget(footer)

        self._scene = left
        self._panel = panel
        self._sidebar_handle = SidebarHandle(self)
        saved_collapsed = self._settings.value("sidebar/collapsed", False, type=bool)
        self._inspector_collapsed = saved_collapsed
        self._sidebar_shortcut = QShortcut(QKeySequence("Ctrl+B"), self)
        self._sidebar_shortcut.activated.connect(self.toggle_sidebar)
        self._root_layout = root_layout
        self._root = root
        self.splitter = FixedSplitter(Qt.Orientation.Horizontal)
        self.splitter.setObjectName("mainSplitter")
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setHandleWidth(1)
        self.splitter.addWidget(self._scene)
        self.splitter.addWidget(self._panel)
        self.splitter.setStretchFactor(0, 72)
        self.splitter.setStretchFactor(1, 28)
        self.splitter.setCollapsible(0, False)
        self.splitter.setCollapsible(1, True)
        self._root_layout.addWidget(self.splitter, 1)
        self.setCentralWidget(root)
        self.setStyleSheet(STYLESHEET)
        self._panel.setMinimumWidth(0 if saved_collapsed else 160)
        self._update_handle()
        self._apply_sidebar_layout()

    def _set_runtime_mode(self, mode: RuntimeMode) -> None:
        self.runtime_mode = mode
        roleplay = mode is RuntimeMode.ROLEPLAY
        self.roleplay_mode_button.setChecked(roleplay)
        self.story_mode_button.setChecked(not roleplay)
        self.mode_status.setText(
            "人物对话模式" if roleplay else "剧情推演入口已开放 · 模拟引擎尚未接入界面"
        )
        self.input.setEnabled(roleplay)
        self.send_button.setEnabled(roleplay and bool(self.input.text().strip()) and self._thread is None)
        self.input.setPlaceholderText("描述你的行动或想说的话……")
        self.input.setAccessibleName("人物扮演对话输入" if roleplay else "剧情推演模式对话输入已停用")
        self.send_button.setAccessibleName("\u53d1\u9001\u5bf9\u8bdd")

    def showEvent(self, event) -> None:  # noqa: N802 - Qt API name
        super().showEvent(event)
        self._apply_sidebar_layout()

    @Slot()
    def toggle_sidebar(self) -> None:
        if self._inspector_collapsed:
            self._expand_sidebar()
        else:
            self._collapse_sidebar()

    def _collapse_sidebar(self) -> None:
        self._inspector_collapsed = True
        self._panel.setMinimumWidth(0)
        self._panel.hide()
        self._settings.setValue("sidebar/collapsed", True)
        self._update_handle()
        self._apply_sidebar_layout()

    def _expand_sidebar(self) -> None:
        self._inspector_collapsed = False
        self._panel.setMinimumWidth(0)
        self._panel.show()
        self._settings.setValue("sidebar/collapsed", False)
        self._update_handle()
        self._apply_sidebar_layout()

    def _apply_sidebar_layout(self) -> None:
        if not hasattr(self, "splitter") or self.splitter.width() <= 0:
            return
        width = self.splitter.width()
        if self._inspector_collapsed:
            self.splitter.setSizes([width, 0])
        else:
            self._panel.setMinimumWidth(min(160, max(0, width - 240)))
            target = max(160, min(560, round(width * 0.28)))
            target = min(target, max(0, width - 240))
            self.splitter.setSizes([max(1, width - target - self.splitter.handleWidth()), target])
        handle = self.splitter.handle(1)
        divider = self.splitter.mapTo(self, handle.pos())
        top = self.splitter.mapTo(self, self.splitter.rect().topLeft()).y()
        self._sidebar_handle.move(divider.x() - self._sidebar_handle.width() // 2,
                                  top + (self.splitter.height() - self._sidebar_handle.height()) // 2)
        self._sidebar_handle.raise_()

    def _update_handle(self) -> None:
        collapsed = self._inspector_collapsed
        self._sidebar_handle._button.setText("◀" if collapsed else "▶")
        name = "展开世界档案" if collapsed else "收起世界档案"
        self._sidebar_handle._button.setAccessibleName(name)
        self._sidebar_handle._button.setToolTip(f"{name}（Ctrl+B）")

    @staticmethod
    def _section(title: str, heading: str, body: str) -> QWidget:
        frame = QFrame()
        frame.setObjectName("infoCard")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(13, 12, 13, 12)
        label = QLabel(title)
        label.setObjectName("sectionTitle")
        layout.addWidget(label)
        if heading:
            main = QLabel(heading)
            main.setObjectName("infoHeading")
            main.setWordWrap(True)
            layout.addWidget(main)
        text = QLabel(body)
        text.setObjectName("infoBody")
        text.setWordWrap(True)
        layout.addWidget(text)
        return frame

    def _refresh_sprite(self) -> None:
        pixmap = self.renderer.render(self.agent.sprite_key)
        self.sprite.setPixmap(pixmap.scaled(330, 390, Qt.AspectRatioMode.KeepAspectRatio,
                                            Qt.TransformationMode.SmoothTransformation))

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt API name
        super().resizeEvent(event)
        self._refresh_sprite()
        self._apply_sidebar_layout()

    def _load_history(self) -> None:
        self.transcript.clear()
        history = self.service.history(self.world)
        if not history:
            if self.world.description.strip():
                self.transcript.append(self._escape(self.world.description))
            if self.agent.persona.strip():
                self.transcript.append(self._escape(self.agent.persona))
            return
        for event in history:
            if event.kind == "player":
                self.transcript.append(f"<p style='color:#e0b58f'><b>你</b><br>{self._escape(event.content)}</p>")
            else:
                safe = self._escape(event.content).replace("\n", "<br>")
                self.transcript.append(f"<p><b>{self._escape(self.agent.name)}</b><br>{safe}</p>")
        scrollbar = self.transcript.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    @staticmethod
    def _escape(text: str) -> str:
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

    def _submit(self) -> None:
        prompt = self.input.text().strip()
        if not prompt:
            return
        self.service.store.append(ConversationEvent.create(self.world.id, self.agent.id, "player", prompt))
        self._load_history()
        self.input.clear()
        self.send_button.setEnabled(False)
        self.status.setText("正在写下这一刻……")
        self._thread = QThread(self)
        self._worker = TurnWorker(self.service, self.world, self.agent, prompt)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._turn_finished)
        self._worker.failed.connect(self._turn_failed)
        self._worker.finished.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._thread.finished.connect(self._clear_worker)
        self._thread.start()

    @Slot(str)
    def _update_send_button(self, text: str) -> None:
        self.send_button.setEnabled(bool(text.strip()) and self._thread is None)

    @Slot(str)
    def _turn_finished(self, _reply: str) -> None:
        self._load_history()
        self.status.setText(f"{self.service.provider.label}  ·  对话保存在本地")
        self._update_send_button(self.input.text())
        self.input.setFocus()

    @Slot(str)
    def _turn_failed(self, message: str) -> None:
        self.status.setText(f"生成失败：{message}（检查 Ollama 配置后可重试）")
        self._update_send_button(self.input.text())
        self.input.setFocus()

    @Slot()
    def _clear_worker(self) -> None:
        if self._worker is not None:
            self._worker.deleteLater()
        if self._thread is not None:
            self._thread.deleteLater()
        self._worker = None
        self._thread = None
        self._update_send_button(self.input.text())


STYLESHEET = """
QMainWindow, QWidget#root { background: #151619; color: #f1e9df; }
QFrame#sceneCard, QFrame#inspector { background: #202126; border: 1px solid #303136; border-radius: 16px; }
QWidget#sidebarHandle { background: transparent; }
QSplitter::handle:horizontal { background: #45434a; width: 1px; }
QPushButton#sidebarHandleButton { background: #27272c; border: 1px solid #4a474c; border-radius: 10px; color: #c5ae9a; font-size: 11px; padding: 0; }
QPushButton#sidebarHandleButton:hover { background: #343036; border-color: #b88a61; color: #f1e9df; }
QPushButton#sidebarHandleButton:focus { border: 2px solid #c48e6b; }
QLabel#eyebrow { color: #cba888; font-size: 10px; font-weight: 700; letter-spacing: 2px; }
QLabel#worldName { color: #a6a0a0; font-size: 11px; }
QPushButton#modeButton { background: #292a30; border: 1px solid #414148; border-radius: 8px; padding: 7px 13px; color: #b9b1ad; font-size: 11px; }
QPushButton#modeButton:hover { border-color: #8d6a55; color: #f1e9df; }
QPushButton#modeButton:checked { background: #c48e6b; border-color: #c48e6b; color: #171719; font-weight: 700; }
QLabel#modeStatus { color: #858187; font-size: 10px; padding-left: 8px; }
QFrame#stage { background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #34343d,stop:0.65 #605d65,stop:1 #29292f); border-radius: 12px; }
QFrame#dialogue { background: #292a30; border: 1px solid #3b3b41; border-radius: 12px; }
QLabel#speaker { color: #e7bd98; font-size: 16px; font-weight: 700; }
QTextBrowser#transcript { background: transparent; border: none; color: #eee4da; font-size: 14px; }
QLineEdit#input { background: #292a30; border: 1px solid #414148; border-radius: 9px; padding: 12px; color: #f4ede5; font-size: 13px; }
QPushButton#sendButton { background: #c48e6b; border: none; border-radius: 9px; padding: 11px 18px; color: #171719; font-weight: 700; }
QPushButton#sendButton:hover { background: #d6a27f; }
QPushButton#sendButton:disabled { background: #76645a; }
QLabel#status { color: #858187; font-size: 10px; }
QLabel#panelTitle { color: #f2e9df; font-size: 19px; font-weight: 700; padding-bottom: 5px; }
QFrame#infoCard { background: #292a30; border: 1px solid #38393f; border-radius: 10px; }
QLabel#sectionTitle { color: #cba888; font-size: 10px; font-weight: 700; }
QLabel#infoHeading { color: #eee4da; font-size: 13px; font-weight: 600; }
QLabel#infoBody { color: #aaa5a2; font-size: 11px; }
QListWidget#memoryList { background: #292a30; border: 1px solid #38393f; border-radius: 9px; padding: 5px; color: #c5bfba; font-size: 11px; }
QListWidget#memoryList::item { padding: 6px 4px; }
"""


# Phase 3 desktop shell. The existing MVP MainWindow above remains the
# service-backed Galgame client; this small window is the mode-neutral UI
# foundation for the roleplay, simulation, and director flows.
from html import escape as _html_escape

from PySide6.QtCore import Signal as _Signal
from PySide6.QtWidgets import (
    QComboBox as _QComboBox,
    QDialog as _QDialog,
    QDialogButtonBox as _QDialogButtonBox,
    QPlainTextEdit as _QPlainTextEdit,
    QToolButton as _QToolButton,
    QApplication as _QApplication,
)

from cognitive_sandbox.domain.dialogue import DialogueLine as _DialogueLine
from cognitive_sandbox.domain.llm_config import LLMConfig as _LLMConfig
from cognitive_sandbox.domain.narrative_event import NarrativeEvent as _NarrativeEvent
from cognitive_sandbox.presentation.ai_settings_panel import AISettingsPanel
from cognitive_sandbox.presentation.scenario_selection import ScenarioSelectionPanel
from cognitive_sandbox.presentation.world_lobby import WorldLobbyPanel
from cognitive_sandbox.presentation.director.director_panel import DirectorPanel


class _ConfirmOnEnterTextEdit(_QPlainTextEdit):
    """Send on Enter while preserving multiline input with Shift+Enter."""

    enter_pressed = _Signal()

    def keyPressEvent(self, event) -> None:  # noqa: N802 - Qt API name
        if (
            event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter)
            and not event.modifiers() & Qt.KeyboardModifier.ShiftModifier
        ):
            self.enter_pressed.emit()
            event.accept()
            return
        super().keyPressEvent(event)


class FoundationMainWindow(QMainWindow):
    """Small desktop shell for Phase 3 UI state and presentation."""

    mode_changed = _Signal(str)
    player_input_confirmed = _Signal(str)

    MODES = ("roleplay", "simulation", "director")

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Cognitive Sandbox")
        self.resize(960, 680)
        self.llm_config: _LLMConfig | None = None
        self.confirmed_input = ""
        self.ui_runtime = None
        self.game_launcher = None
        self.scenario_registry = None
        self.current_session = None
        self.current_world_creation_session = None
        self.character_roster_dialog = None
        self.world_library = WorldLibrary()
        self.world_manager = WorldManager(self.world_library)
        self.current_world_instance_id: str | None = None
        self._is_processing = False
        self._roleplay_thread: QThread | None = None
        self._roleplay_worker = None
        self.message_history: list[DisplayMessage] = []
        self._scenario_presenter = ScenarioPresenter()
        self._requested_entry_mode = "roleplay"
        self.home_dialog = None
        self._simulation_dialog_scheduled = False
        self._simulation_dialog_open = False

        central = QWidget(self)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        header = QHBoxLayout()
        self.mode_selector = _QComboBox(central)
        self.mode_selector.setObjectName("modeSelector")
        for mode, label in (("roleplay", "人物扮演"), ("simulation", "模拟"), ("director", "导演")):
            self.mode_selector.addItem(label, mode)
        self.mode_selector.currentIndexChanged.connect(self._on_mode_changed)
        header.addWidget(QLabel("模式", central))
        header.addWidget(self.mode_selector)
        self.world_context_label = QLabel("未进入世界", central)
        self.world_context_label.setObjectName("worldContextLabel")
        header.addWidget(self.world_context_label)
        header.addStretch(1)
        self.ai_settings_button = _QToolButton(central)
        self.ai_settings_button.setText("AI 设置")
        self.ai_settings_button.clicked.connect(self.open_ai_settings)
        header.addWidget(self.ai_settings_button)
        self.new_game_button = _QToolButton(central)
        self.new_game_button.setText("世界大厅")
        self.new_game_button.clicked.connect(self.open_world_lobby)
        header.addWidget(self.new_game_button)
        self.world_menu_button = _QToolButton(central)
        self.world_menu_button.setObjectName("worldMenuButton")
        self.world_menu_button.setText("世界菜单")
        self.world_menu = QMenu(self.world_menu_button)
        self.save_world_action = self.world_menu.addAction("保存世界")
        self.exit_world_action = self.world_menu.addAction("退出当前世界")
        self.save_world_action.triggered.connect(self.save_current_world)
        self.exit_world_action.triggered.connect(self.exit_current_world)
        self.world_menu_button.setMenu(self.world_menu)
        self.world_menu_button.setPopupMode(_QToolButton.ToolButtonPopupMode.InstantPopup)
        self.world_menu_button.setEnabled(False)
        header.addWidget(self.world_menu_button)
        self.chronicle_button = _QToolButton(central)
        self.chronicle_button.setObjectName("worldChronicleButton")
        self.chronicle_button.setText("世界编年史")
        self.chronicle_button.setEnabled(False)
        self.chronicle_button.clicked.connect(self.open_world_chronicle)
        header.addWidget(self.chronicle_button)
        self.character_roster_button = _QToolButton(central)
        self.character_roster_button.setObjectName("characterRosterButton")
        self.character_roster_button.setText("角色档案")
        self.character_roster_button.setEnabled(False)
        self.character_roster_button.clicked.connect(self.open_character_roster)
        header.addWidget(self.character_roster_button)
        self.debug_button = _QToolButton(central)
        self.debug_button.setObjectName("simulationDebugButton")
        self.debug_button.setText("模拟诊断")
        self.debug_button.setEnabled(False)
        self.debug_button.clicked.connect(self.open_simulation_debug)
        header.addWidget(self.debug_button)
        layout.addLayout(header)

        self.guidance_panel = QFrame(central)
        self.guidance_panel.setObjectName("narrativeOpportunityPanel")
        guidance_layout = QVBoxLayout(self.guidance_panel)
        guidance_layout.setContentsMargins(10, 8, 10, 8)
        guidance_layout.setSpacing(4)
        self.guidance_focus = QLabel("当前关注", self.guidance_panel)
        self.guidance_focus.setObjectName("narrativeOpportunityFocus")
        guidance_layout.addWidget(self.guidance_focus)
        self.opportunity_rows = QVBoxLayout()
        self.opportunity_rows.setContentsMargins(0, 0, 0, 0)
        self.opportunity_rows.setSpacing(4)
        guidance_layout.addLayout(self.opportunity_rows)
        self.guidance_panel.hide()
        layout.addWidget(self.guidance_panel)

        self.narrative_display = QTextBrowser(central)
        self.narrative_display.setObjectName("narrativeDisplay")
        self.narrative_display.setPlaceholderText("叙事与角色对白会显示在这里。")
        layout.addWidget(self.narrative_display, 1)
        self.system_message_label = QLabel(central)
        self.system_message_label.setObjectName("systemMessageStatus")
        self.system_message_label.setWordWrap(True)
        self.system_message_label.hide()
        layout.addWidget(self.system_message_label)

        self.director_panel = DirectorPanel(None, central)
        self.director_panel.hide()
        layout.addWidget(self.director_panel)

        input_row = QHBoxLayout()
        self.player_input = _ConfirmOnEnterTextEdit(central)
        self.player_input.setObjectName("playerInput")
        self.player_input.setPlaceholderText("输入行动或台词……")
        self.player_input.setMaximumHeight(110)
        self.confirm_button = QPushButton("确认", central)
        self.confirm_button.setObjectName("confirmButton")
        self.confirm_button.setEnabled(False)
        self.confirm_button.setText("执行")
        self.wait_button = QPushButton("等待", central)
        self.wait_button.setObjectName("waitButton")
        self.observe_button = QPushButton("观察", central)
        self.observe_button.setObjectName("observeButton")
        self.wait_button.setEnabled(False)
        self.observe_button.setEnabled(False)
        self.player_input.textChanged.connect(self._update_confirm_enabled)
        self.confirm_button.clicked.connect(self.confirm_player_input)
        self.player_input.enter_pressed.connect(self.confirm_button.click)
        input_row.addWidget(self.player_input, 1)
        input_row.addWidget(self.confirm_button)
        input_row.addWidget(self.wait_button)
        input_row.addWidget(self.observe_button)
        self.wait_button.clicked.connect(lambda: self._quick_interaction("wait"))
        self.observe_button.clicked.connect(lambda: self._quick_interaction("observe"))
        self.response_status = QLabel("等待行动", central)
        self.response_status.setObjectName("responseStatus")
        self.response_status.hide()
        input_row.addWidget(self.response_status)
        layout.addLayout(input_row)

        self.setCentralWidget(central)
        self._on_mode_changed(self.mode_selector.currentIndex())
        from cognitive_sandbox.presentation.theme import DARK_STYLESHEET
        self.setStyleSheet(DARK_STYLESHEET)

    @property
    def current_mode(self) -> str:
        return str(self.mode_selector.currentData())

    def set_mode(self, mode: str) -> None:
        if mode not in self.MODES:
            raise ValueError(f"unsupported mode: {mode}")
        index = self.mode_selector.findData(mode)
        self.mode_selector.setCurrentIndex(index)

    def _on_mode_changed(self, _index: int) -> None:
        mode = self.current_mode
        runtime_ready = self.ui_runtime is not None or self.game_launcher is None
        self.player_input.setEnabled(
            mode == "roleplay" and runtime_ready and not self._is_processing
        )
        self.response_status.setVisible(
            self.ui_runtime is not None and mode == "roleplay"
        )
        self.director_panel.setVisible(mode == "director")
        self.guidance_panel.setVisible(mode == "roleplay" and self.opportunity_rows.count() > 0)
        if mode == "director":
            self.director_panel.set_session(self.current_session)
        self._update_confirm_enabled()
        self.mode_changed.emit(mode)
        if (mode == "simulation" and self.current_session is not None
                and not self._simulation_dialog_open and not self._simulation_dialog_scheduled):
            self._simulation_dialog_scheduled = True
            QTimer.singleShot(0, self._open_simulation_for_selected_mode)

    def _open_simulation_for_selected_mode(self):
        self._simulation_dialog_scheduled = False
        if self.current_mode == "simulation" and self.current_session is not None:
            self.open_story_mode(self.current_session)

    @property
    def input_text(self) -> str:
        return self.player_input.toPlainText()

    def _update_confirm_enabled(self) -> None:
        self.confirm_button.setEnabled(
            self.player_input.isEnabled()
            and bool(self.input_text.strip())
            and not self._is_processing
        )
        shortcut_enabled = (
            self.current_mode == "roleplay"
            and self.ui_runtime is not None
            and not self._is_processing
        )
        if hasattr(self, "wait_button"):
            self.wait_button.setEnabled(shortcut_enabled)
            self.observe_button.setEnabled(shortcut_enabled)

    def _quick_interaction(self, intent: str) -> None:
        if self._is_processing or self.ui_runtime is None:
            return
        try:
            self._set_processing(True)
            prepare = getattr(self.ui_runtime, "prepare_interaction_button", None)
            execute = getattr(self.ui_runtime, "execute_confirm", None)
            if callable(prepare) and callable(execute):
                text = prepare(intent)
                self.append_player_message(text)
                self.append_temporary_message("正在生成...")
                self._begin_roleplay_execution(execute)
                return
            # Compatibility for lightweight runtimes used by integrations.
            self.ui_runtime.handle_interaction_button(intent)
        except Exception:
            logger.exception("Could not prepare roleplay shortcut")
            self.append_system_message("行动执行失败，请重试")
        finally:
            if self._is_processing and self._roleplay_thread is None:
                self._set_processing(False)

    def confirm_player_input(self) -> None:
        value = self.input_text.strip()
        if not value or self._is_processing:
            return
        self.confirmed_input = value
        # Capture, clear, and show the user's message before any AI or
        # simulation work begins. This remains true if preparation fails.
        self.player_input.clear()
        self.clear_system_message()
        self.append_player_message(value)
        if self.ui_runtime is None:
            self.player_input_confirmed.emit(value)
            self._update_confirm_enabled()
            return
        try:
            self._set_processing(True)
            self.player_input_confirmed.emit(value)
            self.ui_runtime.handle_player_input(value)
            execute = getattr(self.ui_runtime, "execute_confirm", None)
            if callable(execute):
                self.append_temporary_message("正在生成...")
                self._start_roleplay_worker(execute)
            else:
                # Preserve compatibility for simple in-process UI adapters.
                self.ui_runtime.handle_confirm()
                self._set_processing(False)
        except Exception:
            logger.exception("Could not prepare roleplay input")
            self.append_system_message("行动执行失败，请重试")
            self._set_processing(False)

    def _set_processing(self, processing: bool) -> None:
        self._is_processing = processing
        self.response_status.setText("世界正在响应..." if processing else "等待行动")
        self.response_status.setVisible(self.ui_runtime is not None and self.current_mode == "roleplay")
        self.player_input.setEnabled(
            not processing and self.current_mode == "roleplay" and self.ui_runtime is not None
        )
        self._update_confirm_enabled()

    def _begin_roleplay_execution(self, operation) -> None:
        self._set_processing(True)
        self._start_roleplay_worker(operation)

    def _start_roleplay_worker(self, operation) -> None:
        from cognitive_sandbox.presentation.roleplay.roleplay_worker import RoleplayWorker

        if self._roleplay_thread is not None and self._roleplay_thread.isRunning():
            return
        thread = QThread(self)
        worker = RoleplayWorker(operation)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.succeeded.connect(self._on_roleplay_succeeded)
        worker.failed.connect(self._on_roleplay_failed)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(self._on_roleplay_thread_finished)
        thread.finished.connect(thread.deleteLater)
        self._roleplay_thread = thread
        self._roleplay_worker = worker
        thread.start()

    @Slot(object)
    def _on_roleplay_succeeded(self, result) -> None:
        try:
            self.clear_system_message()
            presenter = getattr(self.ui_runtime, "present_result", None)
            if callable(presenter):
                presenter(result)
            self._refresh_world_context()
        except Exception:
            logger.exception("Could not display roleplay result")
            self.append_system_message("行动执行失败，请重试")

    @Slot(str)
    def _on_roleplay_failed(self, _details: str) -> None:
        # Details are logged in the worker; keep the player-facing error useful
        # without leaking provider or implementation diagnostics.
        recover = getattr(self.ui_runtime, "recover_failed_execution", None)
        if callable(recover):
            recover()
        self.clear_system_message()
        self.append_system_message("行动执行失败，请重试")

    @Slot()
    def _on_roleplay_thread_finished(self) -> None:
        self._roleplay_worker = None
        self._roleplay_thread = None
        self._set_processing(False)

    def set_ui_runtime(self, runtime) -> None:
        self.ui_runtime = runtime
        self.player_input.setEnabled(
            self.current_mode == "roleplay" and runtime is not None and not self._is_processing
        )
        self.response_status.setText("等待行动")
        self.response_status.setVisible(runtime is not None and self.current_mode == "roleplay")
        self._update_confirm_enabled()
        refresh_guidance = getattr(runtime, "refresh_guidance", None)
        if callable(refresh_guidance):
            refresh_guidance()

    def set_narrative_opportunities(self, opportunities, *, focus="") -> None:
        """Render only opportunities already filtered for the active character."""
        while self.opportunity_rows.count():
            item = self.opportunity_rows.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        values = tuple(opportunities or ())[:3]
        self.guidance_panel.setVisible(bool(values) and self.current_mode == "roleplay")
        self.guidance_focus.setText(f"值得注意 · 当前关注：{focus}" if focus else "值得注意")
        for opportunity in values:
            row = QWidget(self.guidance_panel)
            row_layout = QVBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            description = QLabel(opportunity.description, row)
            description.setWordWrap(True)
            row_layout.addWidget(description)
            actions = QHBoxLayout()
            for suggestion in opportunity.possible_actions[:3]:
                button = QPushButton(suggestion, row)
                button.setObjectName("opportunitySuggestionButton")
                button.clicked.connect(lambda _checked=False, text=suggestion: self._fill_player_input(text))
                actions.addWidget(button)
            row_layout.addLayout(actions)
            self.opportunity_rows.addWidget(row)
        self.guidance_panel.adjustSize()

    def _fill_player_input(self, text):
        self.player_input.setPlainText(text)
        self.player_input.setFocus()

    def set_game_launcher(self, launcher) -> None:
        if not callable(getattr(launcher, "start_scenario", None)):
            raise TypeError("launcher must provide start_scenario.")
        registry = getattr(getattr(launcher, "scenario_loader", None), "registry", None)
        if registry is None:
            raise TypeError("launcher must expose a scenario registry through its loader.")
        self.game_launcher = launcher
        self.scenario_registry = registry
        self.player_input.setEnabled(self.current_mode == "roleplay" and self.ui_runtime is not None)
        self._update_confirm_enabled()

    def open_home(self) -> None:
        from cognitive_sandbox.presentation.home import HomePage
        dialog = HomePage(self.world_library, self)
        self.home_dialog = dialog
        dialog.enter_world.connect(lambda mode: self._home_open_lobby(dialog, mode))
        dialog.observe_simulation.connect(lambda: self._home_open_lobby(dialog, "simulation"))
        dialog.director_mode.connect(lambda: self._home_open_lobby(dialog, "director"))
        dialog.create_world.connect(lambda: (dialog.accept(), QTimer.singleShot(0, self.open_ai_world_creation)))
        dialog.debug_requested.connect(lambda: (dialog.accept(), QTimer.singleShot(0, self.open_simulation_debug)))
        dialog.exec()

    def _home_open_lobby(self, dialog, mode):
        self._requested_entry_mode = mode
        dialog.accept()
        QTimer.singleShot(0, lambda: self.open_world_lobby(mode=mode))

    def open_scenario_selection(self) -> None:
        if self.scenario_registry is None or self.game_launcher is None:
            return
        dialog = _QDialog(self)
        dialog.setWindowTitle("新游戏")
        layout = QVBoxLayout(dialog)
        panel = ScenarioSelectionPanel(self.scenario_registry, dialog)
        layout.addWidget(panel)
        create_world_button = QPushButton("AI 创建世界", dialog)
        create_world_button.setObjectName("createWorldButton")
        layout.addWidget(create_world_button)
        back_button = QPushButton("返回世界大厅", dialog)
        back_button.setObjectName("returnToWorldLobbyButton")
        layout.addWidget(back_button)

        def _start(scenario_id: str) -> None:
            self.start_new_game(scenario_id)
            dialog.accept()

        panel.scenario_started.connect(_start)
        create_world_button.clicked.connect(
            lambda: (dialog.accept(), QTimer.singleShot(0, self.open_ai_world_creation))
        )
        back_button.clicked.connect(lambda: (dialog.reject(), QTimer.singleShot(0, self.open_world_lobby)))
        dialog.exec()

    def open_world_lobby(self, mode=None) -> None:
        if self.game_launcher is None:
            return
        if mode in self.MODES:
            self._requested_entry_mode = mode
        dialog = _QDialog(self)
        dialog.setWindowTitle("世界大厅")
        dialog.setObjectName("worldLobbyDialog")
        layout = QVBoxLayout(dialog)
        panel = WorldLobbyPanel(self.world_library, self.scenario_registry, dialog)
        if self.current_world_instance_id is not None:
            for index in range(panel.world_list.count()):
                item = panel.world_list.item(index)
                if item.data(Qt.ItemDataRole.UserRole) == self.current_world_instance_id:
                    panel.world_list.setCurrentItem(item)
                    break
        layout.addWidget(panel)

        def _continue() -> None:
            selected_id = panel.selected_world_id
            if selected_id is None:
                return
            try:
                self.switch_world(selected_id)
                self.set_mode(self._requested_entry_mode)
            except Exception as error:
                self.append_system_message(f"无法恢复这个世界：{error}")
                panel.refresh()
                return
            dialog.accept()

        panel.continue_requested.connect(lambda _instance_id: _continue())
        panel.delete_requested.connect(lambda instance_id: self._delete_world_from_lobby(instance_id, panel))
        panel.create_requested.connect(
            lambda: (dialog.accept(), QTimer.singleShot(0, self.open_ai_world_creation))
        )
        def _start_scenario(scenario_id: str) -> None:
            try:
                session = self.game_launcher.start_world(scenario_id)
                if self._requested_entry_mode == "simulation":
                    session.scenario_settings = {**session.scenario_settings,
                                                 "mode": "simulation_observation"}
                self.mode_selector.setCurrentIndex(self.mode_selector.findData(self._requested_entry_mode))
                self._attach_roleplay_session(session)
                self.set_mode(self._requested_entry_mode)
                dialog.accept()
            except Exception as error:
                logger.exception("Could not start scenario package")
                self.append_system_message("无法启动这个世界，请稍后重试。")
                panel.refresh()

        panel.scenario_requested.connect(_start_scenario)
        panel.extend_requested.connect(
            lambda instance_id: (dialog.accept(), QTimer.singleShot(0, lambda: self.open_world_extension(instance_id)))
        )
        dialog.exec()

    def _delete_world_from_lobby(self, instance_id, panel) -> None:
        from PySide6.QtWidgets import QMessageBox

        if self.world_library.active_id == instance_id:
            self.append_system_message("当前世界正在运行，请先退出世界再删除。")
            panel.refresh()
            return
        answer = QMessageBox.question(
            panel,
            "删除世界",
            "确定删除这个世界吗？它的存档、对话和世界数据都会一并删除。此操作无法撤销。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer is not QMessageBox.StandardButton.Yes:
            return
        try:
            self.world_manager.delete_world(instance_id)
            panel.refresh()
        except WorldLifecycleError as error:
            self.append_system_message(str(error))
        except Exception:
            logger.exception("Could not delete world instance")
            self.append_system_message("删除世界失败，请稍后重试。")

    def open_story_mode(self, session=None) -> None:
        session = session or self.current_session
        if session is None:
            return
        from cognitive_sandbox.presentation.simulation.simulation_view import SimulationView
        dialog = _QDialog(self)
        dialog.setWindowTitle("模拟观察")
        dialog.resize(680, 560)
        self._simulation_dialog_open = True
        layout = QVBoxLayout(dialog)
        story_view = SimulationView(session, dialog)
        layout.addWidget(story_view)
        def _switch_to_player_mode() -> None:
            self.mode_selector.setCurrentIndex(self.mode_selector.findData("roleplay"))
            dialog.accept()
        story_view.player_mode_requested.connect(_switch_to_player_mode)
        close_button = QPushButton("返回世界", dialog)
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button)
        dialog.exec()
        self._simulation_dialog_open = False

    def open_world_extension(self, instance_id: str) -> None:
        """Draft and explicitly confirm an append-only patch for one world."""
        from cognitive_sandbox.application.world_evolution_manager import WorldEvolutionManager
        from cognitive_sandbox.application.world_patch_drafter import WorldPatchDrafter
        from cognitive_sandbox.domain.patch_validation_result import PatchValidationStatus
        from cognitive_sandbox.domain.world_patch import WorldPatch, WorldPatchType

        if instance_id not in {world.instance_id for world in self.world_library.list_worlds()}:
            self.append_system_message("无法扩展：这个世界实例已不存在。")
            return
        dialog = _QDialog(self)
        dialog.setWindowTitle("扩展世界 · 添加角色")
        dialog.setObjectName("worldExtensionDialog")
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("描述要加入世界的新角色", dialog))
        prompt = _QPlainTextEdit(dialog)
        prompt.setObjectName("worldPatchPrompt")
        prompt.setPlaceholderText("例如：加入一名在第十天收到求救信号后抵达医疗中心的流浪商人")
        prompt.setMaximumHeight(90)
        layout.addWidget(prompt)
        generate_button = QPushButton("生成角色草案", dialog)
        generate_button.setObjectName("generateWorldPatchButton")
        layout.addWidget(generate_button)
        preview = QLabel("草案只会写入该世界实例的追加记录；确认后从当前时间点生效。", dialog)
        preview.setObjectName("worldPatchPreview")
        preview.setWordWrap(True)
        layout.addWidget(preview)
        status = QLabel("", dialog)
        status.setObjectName("worldPatchStatus")
        status.setWordWrap(True)
        layout.addWidget(status)
        confirm_button = QPushButton("确认加入", dialog)
        confirm_button.setObjectName("confirmWorldPatchButton")
        confirm_button.setEnabled(False)
        layout.addWidget(confirm_button)

        manager = WorldEvolutionManager(self.world_library)
        patch_holder: dict[str, WorldPatch] = {}

        def _make_drafter():
            provider = None
            settings = QSettings("CognitiveSandbox", "CognitiveSandbox")
            if all(settings.contains(f"ai/{key}") for key in ("provider", "model_name", "base_url")):
                try:
                    from cognitive_sandbox.application.llm_provider import LLMProvider
                    wiring = getattr(self.game_launcher, "ai_runtime_wiring", None)
                    provider = LLMProvider(wiring.load_config()) if wiring is not None else None
                except (TypeError, ValueError):
                    provider = None
            return WorldPatchDrafter(provider)

        def _generate() -> None:
            try:
                patch = _make_drafter().draft_character(prompt.toPlainText())
                result = manager.validate(instance_id, patch)
            except Exception as error:
                status.setText(f"无法生成草案：{error}")
                confirm_button.setEnabled(False)
                return
            patch_holder["patch"] = patch
            addition = patch.payload
            card = addition.character_card
            preview.setText(
                f"{card.name} · {card.occupation}\n"
                f"性格：{'、'.join(card.personality) or '未指定'}\n"
                f"背景：{card.background}\n"
                f"加入方式：{addition.introduction_method}\n"
                f"出现条件：{addition.appearance_condition}\n"
                f"入场事件：{addition.entry_event}\n"
                f"生效时间：{patch.effective_time}"
            )
            status.setText("\n".join(result.reasons) or "未发现已知冲突。请确认后加入。")
            confirm_button.setEnabled(result.status is not PatchValidationStatus.REJECTED)

        def _confirm() -> None:
            patch = patch_holder.get("patch")
            if patch is None:
                return
            result = manager.apply(instance_id, patch, confirmed=True)
            if result.status is PatchValidationStatus.REJECTED:
                status.setText("补丁被拒绝：" + "\n".join(result.reasons))
                return
            self.append_system_message(f"世界补丁已加入：{patch.title}（从{patch.effective_time}生效）")
            dialog.accept()

        generate_button.clicked.connect(_generate)
        confirm_button.clicked.connect(_confirm)
        dialog.exec()

    def switch_world(self, instance_id: str):
        self.clear_system_message()
        session, saved_messages = self.world_library.activate(instance_id, self.message_history)
        self.current_world_instance_id = instance_id
        self.current_session = session
        self._refresh_world_context()
        self.character_roster_button.setEnabled(True)
        self.director_panel.set_session(session)
        self.confirmed_input = ""
        self.player_input.clear()
        story_types = {MessageType.PLAYER, MessageType.CHARACTER, MessageType.NARRATION}
        self.message_history = [message for message in saved_messages
                               if message.message_type in story_types]
        self.narrative_display.clear()
        for message in self.message_history:
            self._render_message(message)
        if self.game_launcher is not None:
            self.game_launcher.current_session = session
        return self._attach_roleplay_session(session, register_world=False, show_opening=False)

    def _create_ai_world_creation_dialog(self):
        if self.game_launcher is None:
            raise RuntimeError("GameLauncher has not been configured.")
        create_session = getattr(self.game_launcher, "create_world_creation_session", None)
        if not callable(create_session):
            raise RuntimeError("GameLauncher does not support AI world creation.")
        creation_session = create_session()
        self.current_world_creation_session = creation_session

        dialog = _QDialog(self)
        dialog.setWindowTitle("AI 创建世界")
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("描述你想玩的世界", dialog))
        prompt = _QPlainTextEdit(dialog)
        prompt.setObjectName("worldPrompt")
        prompt.setPlaceholderText("例如：一座被浓雾笼罩、资源紧缺的海港城市……")
        prompt.setMaximumHeight(100)
        layout.addWidget(prompt)
        generate_button = QPushButton("生成草稿", dialog)
        generate_button.setObjectName("generateWorldButton")
        layout.addWidget(generate_button)
        world_name = QLabel("", dialog)
        world_name.setObjectName("worldDraftName")
        layout.addWidget(world_name)
        world_description = QLabel("", dialog)
        world_description.setObjectName("worldDraftDescription")
        world_description.setWordWrap(True)
        layout.addWidget(world_description)
        layout.addWidget(QLabel("选择或创建你的角色", dialog))
        player_character = _QComboBox(dialog)
        player_character.setObjectName("playerCharacterSelector")
        layout.addWidget(player_character)
        create_player_button = QPushButton("创建玩家角色", dialog)
        create_player_button.setObjectName("createPlayerCharacterButton")
        layout.addWidget(create_player_button)
        characters = QListWidget(dialog)
        characters.setObjectName("worldDraftCharacters")
        layout.addWidget(characters)
        layout.addWidget(QLabel("初始事件（不会自动执行）", dialog))
        events = QListWidget(dialog)
        events.setObjectName("worldDraftEvents")
        layout.addWidget(events)
        status = QLabel("", dialog)
        status.setObjectName("worldGenerationStatus")
        status.setWordWrap(True)
        layout.addWidget(status)
        confirm_button = QPushButton("确认创建并开始", dialog)
        confirm_button.setObjectName("confirmWorldCreationButton")
        confirm_button.setEnabled(False)
        layout.addWidget(confirm_button)

        def _generate() -> None:
            if not prompt.toPlainText().strip():
                status.setText("请输入世界描述。")
                confirm_button.setEnabled(False)
                return
            try:
                result = creation_session.generate(prompt.toPlainText())
            except Exception:
                logger.exception("World generation failed")
                status.setText("暂时无法生成世界，请检查描述后重试。")
                confirm_button.setEnabled(False)
                return
            if result.scenario_content is None or not result.validation_result.valid:
                status.setText("世界草稿未通过检查，请调整描述后重新生成。")
                confirm_button.setEnabled(False)
                return
            content = result.scenario_content
            assert content.world_document is not None
            world_name.setText(content.world_document.name)
            world_description.setText(content.world_document.description)
            characters.clear()
            player_character.clear()
            for card in content.character_cards:
                role = f" · {card.occupation}" if card.occupation else ""
                characters.addItem(f"{card.name}{role}")
                player_character.addItem(card.name, card.character_id)
            events.clear()
            for card in content.event_cards:
                events.addItem(f"{card.name} · {card.description}")
            status.setText("\n".join(result.warnings))
            confirm_button.setEnabled(True)

        def _confirm_and_start() -> None:
            try:
                creation_session.confirm()
                session = creation_session.start(player_character.currentData())
                self._attach_roleplay_session(session)
            except Exception:
                logger.exception("Generated world could not be started")
                status.setText("无法启动这个世界，请检查世界内容后重试。")
                return
            dialog.accept()

        def _create_player_character() -> None:
            result = creation_session.generation_result
            content = result.scenario_content if result is not None else None
            if content is None:
                status.setText("请先生成世界草稿。")
                return
            name, accepted = QInputDialog.getText(dialog, "创建玩家角色", "角色名称")
            if not accepted or not name.strip():
                return
            from dataclasses import replace
            from uuid import uuid4
            from cognitive_sandbox.domain.character_card import CharacterCard
            card = CharacterCard(
                f"player_{uuid4().hex[:10]}", name.strip(), occupation="玩家角色",
                personality=("由玩家创建",), goals=("按照自己的想法探索世界",),
            )
            updated = replace(content, character_cards=(*content.character_cards, card))
            creation_session.scenario_content = updated
            creation_session.generation_result = replace(result, scenario_content=updated)
            player_character.addItem(card.name, card.character_id)
            player_character.setCurrentIndex(player_character.count() - 1)
            characters.addItem(f"{card.name} · 玩家角色")

        back_button = QPushButton("返回世界大厅", dialog)
        back_button.setObjectName("returnToWorldLobbyButton")
        layout.addWidget(back_button)
        back_button.clicked.connect(lambda: (dialog.reject(), QTimer.singleShot(0, self.open_world_lobby)))

        generate_button.clicked.connect(_generate)
        confirm_button.clicked.connect(_confirm_and_start)
        create_player_button.clicked.connect(_create_player_character)
        return dialog

    def open_ai_world_creation(self) -> None:
        if self.game_launcher is None:
            return
        try:
            dialog = self._create_ai_world_creation_dialog()
        except Exception as error:
            logger.exception("Could not create AI world")
            self.append_system_message("暂时无法创建世界，请检查输入后重试。")
            return
        dialog.exec()

    def start_new_game(self, scenario_id: str):
        if self.game_launcher is None:
            raise RuntimeError("GameLauncher has not been configured.")
        session = self.game_launcher.start_scenario(scenario_id)
        result = self._attach_roleplay_session(session)
        if self._requested_entry_mode in self.MODES:
            self.set_mode(self._requested_entry_mode)
        return result

    def _attach_roleplay_session(self, session, *, register_world: bool = True, show_opening: bool = True):
        from cognitive_sandbox.presentation.ui_runtime import UIRuntime

        self.clear_system_message()
        self.current_session = session
        self.character_roster_button.setEnabled(True)
        self.director_panel.set_session(session)
        self.chronicle_button.setEnabled(True)
        self.debug_button.setEnabled(True)
        if self.game_launcher is not None:
            self.game_launcher.current_session = session
        if register_world:
            self.world_library.save_active(self.message_history)
            world = self.world_library.register(session)
            self.current_world_instance_id = world.instance_id
            self.message_history = []
            self.narrative_display.clear()
        UIRuntime(self, session, show_opening=show_opening and not self.message_history)
        self.world_menu_button.setEnabled(True)
        self._refresh_world_context()
        return session

    def _refresh_world_context(self):
        session = self.current_session
        if session is None:
            self.world_context_label.setText("未进入世界")
            return
        content = getattr(session, "scenario_content", None)
        world_document = getattr(content, "world_document", None) if content is not None else None
        scenario = getattr(session, "scenario", None)
        world_name = (
            getattr(world_document, "name", None)
            or getattr(scenario, "name", None)
            or session.world_state.get("world_name")
            or "当前世界"
        )
        names = self._scenario_presenter.display_names(session)
        character = getattr(session, "agent_context", None)
        character_state = getattr(character, "character_state", None)
        character_name = names.get(session.player_id) or getattr(character_state, "name", None)
        if not character_name or character_name.casefold() == session.player_id.casefold():
            character_name = "玩家角色"
        clock = getattr(getattr(session, "executor", None), "world_clock", None)
        when = clock.current_time() if clock is not None else None
        presence_manager = getattr(session, "presence_manager", None)
        presence = presence_manager.get(session.player_id) if presence_manager is not None else None
        location = getattr(presence, "current_location", None)
        location_manager = getattr(session.executor, "location_manager", None)
        location_state = location_manager.get(location) if location and location_manager else None
        if location_state is None and location_manager is not None:
            location_state = next(
                (item for item in location_manager.locations if item.name == location),
                None,
            )
        if location_state is None and location_manager is not None and not location:
            location_state = location_manager.get(location_manager.current_location_id)
        location_name = getattr(location_state, "name", None)
        if not location_name:
            location_name = session.world_state.get("location_name") or session.world_state.get("current_location_name")
        if not location_name:
            location_name = "所在地点"
        started = getattr(session, "scenario_started_at", None)
        day_number = 1
        saved_day = session.world_state.get("day", session.world_state.get("day_number"))
        if isinstance(saved_day, int) and not isinstance(saved_day, bool) and saved_day > 0:
            day_number = saved_day
        if when is not None and started:
            try:
                start_time = datetime.fromisoformat(str(started).replace("Z", "+00:00"))
                if start_time.tzinfo is None:
                    start_time = start_time.replace(tzinfo=when.tzinfo)
                day_number = max(1, (when - start_time).days + 1)
            except (TypeError, ValueError):
                day_number = 1
        values = [f"《{world_name}》", f"角色：{character_name}", f"地点：{location_name}"]
        values.append(f"时间：Day {day_number}" + (f" · {when:%H:%M}" if when is not None else ""))
        self.world_context_label.setText(" · ".join(values))

    def open_character_roster(self):
        if self.current_session is None:
            return None
        from cognitive_sandbox.presentation.character_roster import CharacterRosterDialog
        self.character_roster_dialog = CharacterRosterDialog(self.current_session, self)
        self.character_roster_dialog.exec()
        return self.character_roster_dialog

    def open_world_chronicle(self) -> None:
        """Show a read-only timeline for the active world's events and state changes."""
        session = self.current_session
        if session is None:
            return
        executor = session.executor
        dialog = _QDialog(self)
        dialog.setWindowTitle("世界编年史")
        dialog.resize(560, 440)
        layout = QVBoxLayout(dialog)
        from cognitive_sandbox.presentation.world_chronicle import WorldChroniclePanel

        layout.addWidget(WorldChroniclePanel(
            getattr(executor, "event_timeline", None),
            getattr(getattr(executor, "world_evolution_engine", None), "state_changes", ()),
            location_manager=getattr(executor, "location_manager", None),
            goal_manager=getattr(executor, "goal_manager", None),
            parent=dialog,
        ))
        close_button = QPushButton("关闭", dialog)
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button)
        dialog.exec()

    def open_simulation_debug(self) -> None:
        """Open read-only diagnostics for the active runtime session."""
        if self.current_session is None:
            return
        dialog = _QDialog(self)
        dialog.setWindowTitle("Simulation Debug")
        dialog.resize(900, 680)
        layout = QVBoxLayout(dialog)
        from cognitive_sandbox.presentation.debug.debug_dashboard import DebugDashboard

        layout.addWidget(DebugDashboard(self.current_session, dialog))
        close_button = QPushButton("关闭", dialog)
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button)
        dialog.exec()

    def append_narrative_event(self, event: _NarrativeEvent) -> None:
        if not isinstance(event, _NarrativeEvent):
            raise TypeError("event must be a NarrativeEvent")
        self.append_message(MessageType.NARRATION, event.description)

    def append_dialogue_line(self, line: _DialogueLine) -> None:
        if not isinstance(line, _DialogueLine):
            raise TypeError("line must be a DialogueLine")
        names = self._scenario_presenter.display_names(self.current_session) if self.current_session else {}
        name = names.get(line.speaker_id)
        if not name and self.current_session is not None:
            context = next((item for item in self.current_session.agent_contexts
                            if item.character_id == line.speaker_id), None)
            candidate = getattr(getattr(context, "character_state", None), "name", "")
            if isinstance(candidate, str) and candidate.strip() and candidate.casefold() != line.speaker_id.casefold():
                name = candidate.strip()
        self.append_message(
            MessageType.CHARACTER,
            line.text,
            speaker_id=name,
        )

    def append_opening_message(self, message: str) -> None:
        self.append_message(MessageType.NARRATION, message)

    def append_observation_feedback(self, message: str) -> None:
        self.append_message(MessageType.NARRATION, message)

    def append_player_message(self, message: str) -> None:
        self.append_message(MessageType.PLAYER, message)

    def append_message(
        self,
        message_type: MessageType | str,
        content: str,
        *,
        speaker_id: str | None = None,
    ) -> DisplayMessage:
        message = DisplayMessage(message_type, content, speaker_id)
        if message.message_type in {
            MessageType.SYSTEM_TEMP, MessageType.SYSTEM_ERROR, MessageType.SYSTEM,
        }:
            self._show_system_message(message)
            return message
        self.message_history.append(message)
        self._render_message(message)
        self.world_library.save_active(self.message_history)
        return message

    def _render_message(self, message: DisplayMessage) -> None:
        if message.message_type in {
            MessageType.SYSTEM_TEMP, MessageType.SYSTEM_ERROR, MessageType.SYSTEM,
        }:
            return
        escaped_content = _html_escape(message.content).replace("\n", "<br>")
        if message.message_type is MessageType.PLAYER:
            html = f"<p><span style='color:#e0b58f'>你：</span><br>{escaped_content}</p>"
        elif message.message_type is MessageType.CHARACTER:
            speaker = message.speaker_id
            if speaker and speaker != "世界":
                html = f"<p><span style='color:#c5a35a'>{_html_escape(speaker)}：</span><br>{escaped_content}</p>"
            else:
                html = f"<p>{escaped_content}</p>"
        else:
            html = f"<p>{escaped_content}</p>"
        self.narrative_display.append(html)

    def append_system_message(self, message: str) -> None:
        if not isinstance(message, str) or not message.strip():
            raise ValueError("message must not be empty")
        self.append_message(MessageType.SYSTEM_ERROR, message)

    def append_temporary_message(self, message: str) -> None:
        if not isinstance(message, str) or not message.strip():
            raise ValueError("message must not be empty")
        self.append_message(MessageType.SYSTEM_TEMP, message)

    def _show_system_message(self, message: DisplayMessage) -> None:
        self.system_message_label.setText(message.content)
        self.system_message_label.setProperty("messageType", message.message_type.value)
        self.system_message_label.show()

    def clear_system_message(self) -> None:
        self.system_message_label.clear()
        self.system_message_label.hide()

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt API name
        if self._roleplay_thread is not None and self._roleplay_thread.isRunning():
            self.append_system_message("当前行动完成后即可关闭窗口。")
            event.ignore()
            return
        self.world_library.save_active(self.message_history)
        super().closeEvent(event)

    def save_current_world(self) -> bool:
        if self.current_session is None:
            return False
        self.world_library.save_active(self.message_history)
        if self.current_world_instance_id in self.world_library.persistence_errors:
            self.append_system_message("世界暂时无法保存，请检查存储空间后重试。")
            return False
        self.append_system_message("世界已保存。")
        return True

    def exit_current_world(self) -> None:
        if self.current_session is None:
            self.open_world_lobby()
            return
        saved = self.world_library.deactivate(self.message_history)
        if not saved:
            self.append_system_message("世界暂时无法保存，仍留在当前世界。")
            return
        self.current_session = None
        self.ui_runtime = None
        if self.game_launcher is not None:
            self.game_launcher.current_session = None
        self.current_world_instance_id = None
        self.message_history = []
        self.confirmed_input = ""
        self.player_input.clear()
        self.narrative_display.clear()
        self.world_context_label.setText("未进入世界")
        self.set_narrative_opportunities((), focus="")
        self.character_roster_button.setEnabled(False)
        self.chronicle_button.setEnabled(False)
        self.debug_button.setEnabled(False)
        self.world_menu_button.setEnabled(False)
        self.director_panel.set_session(None)
        self.set_mode("roleplay")
        self.open_world_lobby()

    def open_ai_settings(self) -> None:
        dialog = _QDialog(self)
        dialog.setWindowTitle("AI 设置")
        layout = QVBoxLayout(dialog)
        panel = AISettingsPanel(dialog)
        if self.llm_config is not None:
            panel.load_config(self.llm_config)
        layout.addWidget(panel)
        buttons = _QDialogButtonBox(
            _QDialogButtonBox.StandardButton.Ok | _QDialogButtonBox.StandardButton.Cancel,
            parent=dialog,
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        if dialog.exec() == _QDialog.DialogCode.Accepted:
            panel.save_settings()
            self.llm_config = panel.to_config()
