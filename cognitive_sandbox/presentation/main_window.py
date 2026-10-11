from __future__ import annotations

from PySide6.QtCore import QObject, QSettings, QTimer, Qt, QThread, Signal, Slot
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QButtonGroup, QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget, QMainWindow, QSplitter, QSplitterHandle,
    QPushButton, QSizePolicy, QTextBrowser, QVBoxLayout, QWidget,
)

from cognitive_sandbox.application.service import SandboxService
from cognitive_sandbox.domain.models import Agent, CognitiveMemory, ConversationEvent, World
from cognitive_sandbox.domain.runtime_mode import RuntimeMode
from cognitive_sandbox.infrastructure.static_sprites import StaticSpriteRenderer


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
        self.setWindowTitle("Cognitive Sandbox · 暮港来信")
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
        scene = QLabel("第一章  ·  灯塔亮起之前")
        scene.setObjectName("chapter")
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
        self.input.setPlaceholderText("和林夏说些什么……")
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
        self.input.setPlaceholderText("和林夏说些什么……")
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
            self.transcript.append("<span style='color:#f0c8a2'>傍晚的海风吹进灯塔值班室。</span>")
            self.transcript.append("林夏把一封泛黄的信放在桌上，抬头看向你。<br>“你来得正好。我一直在想，这封信该不该寄出去。”")
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
QLabel#chapter { color: #a6a0a0; font-size: 11px; }
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
        self._is_processing = False

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
        header.addStretch(1)
        self.ai_settings_button = _QToolButton(central)
        self.ai_settings_button.setText("AI 设置")
        self.ai_settings_button.clicked.connect(self.open_ai_settings)
        header.addWidget(self.ai_settings_button)
        self.new_game_button = _QToolButton(central)
        self.new_game_button.setText("新游戏")
        self.new_game_button.clicked.connect(self.open_scenario_selection)
        header.addWidget(self.new_game_button)
        layout.addLayout(header)

        self.narrative_display = QTextBrowser(central)
        self.narrative_display.setObjectName("narrativeDisplay")
        self.narrative_display.setPlaceholderText("叙事与角色对白会显示在这里。")
        layout.addWidget(self.narrative_display, 1)

        input_row = QHBoxLayout()
        self.player_input = _ConfirmOnEnterTextEdit(central)
        self.player_input.setObjectName("playerInput")
        self.player_input.setPlaceholderText("输入行动或台词……")
        self.player_input.setMaximumHeight(110)
        self.confirm_button = QPushButton("确认", central)
        self.confirm_button.setObjectName("confirmButton")
        self.confirm_button.setEnabled(False)
        self.player_input.textChanged.connect(self._update_confirm_enabled)
        self.confirm_button.clicked.connect(self.confirm_player_input)
        self.player_input.enter_pressed.connect(self.confirm_button.click)
        input_row.addWidget(self.player_input, 1)
        input_row.addWidget(self.confirm_button)
        self.response_status = QLabel("AI 正在响应…", central)
        self.response_status.setObjectName("responseStatus")
        self.response_status.hide()
        input_row.addWidget(self.response_status)
        layout.addLayout(input_row)

        self.setCentralWidget(central)
        self._on_mode_changed(self.mode_selector.currentIndex())
        self.setStyleSheet(
            "QMainWindow, QWidget { background: #17181b; color: #eee6de; }"
            "QTextBrowser, QPlainTextEdit { background: #222329; border: 1px solid #414148;"
            " border-radius: 8px; padding: 8px; }"
            "QPushButton, QToolButton, QComboBox { background: #302f35; border: 1px solid #514d52;"
            " border-radius: 7px; padding: 7px 12px; }"
            "QPushButton:disabled { color: #77747a; }"
        )

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
        self.player_input.setEnabled(mode == "roleplay" and runtime_ready)
        self._update_confirm_enabled()
        self.mode_changed.emit(mode)

    @property
    def input_text(self) -> str:
        return self.player_input.toPlainText()

    def _update_confirm_enabled(self) -> None:
        self.confirm_button.setEnabled(
            self.player_input.isEnabled()
            and bool(self.input_text.strip())
            and not self._is_processing
        )

    def confirm_player_input(self) -> None:
        value = self.input_text.strip()
        if not value or self._is_processing:
            return
        self.confirmed_input = value
        self._is_processing = True
        self._update_confirm_enabled()
        if self.ui_runtime is not None:
            self.response_status.show()
            _QApplication.processEvents()
        try:
            if self.ui_runtime is not None:
                self.ui_runtime.handle_player_input(value)
                self.ui_runtime.handle_confirm()
            self.player_input_confirmed.emit(value)
            self.player_input.clear()
        finally:
            self._is_processing = False
            self.response_status.hide()
            self._update_confirm_enabled()

    def set_ui_runtime(self, runtime) -> None:
        self.ui_runtime = runtime
        self.player_input.setEnabled(self.current_mode == "roleplay" and runtime is not None)
        self._update_confirm_enabled()

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

        def _start(scenario_id: str) -> None:
            self.start_new_game(scenario_id)
            dialog.accept()

        panel.scenario_started.connect(_start)
        create_world_button.clicked.connect(
            lambda: (dialog.accept(), QTimer.singleShot(0, self.open_ai_world_creation))
        )
        dialog.exec()

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
        layout.addWidget(QLabel("角色", dialog))
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
            try:
                result = creation_session.generate(prompt.toPlainText())
            except Exception as error:
                status.setText(f"生成失败：{error}")
                confirm_button.setEnabled(False)
                return
            if result.scenario_content is None or not result.validation_result.valid:
                status.setText(result.error or "生成内容未通过验证。")
                confirm_button.setEnabled(False)
                return
            content = result.scenario_content
            assert content.world_document is not None
            world_name.setText(content.world_document.name)
            world_description.setText(content.world_document.description)
            characters.clear()
            for card in content.character_cards:
                role = f" · {card.occupation}" if card.occupation else ""
                characters.addItem(f"{card.name}{role}")
            events.clear()
            for card in content.event_cards:
                events.addItem(f"{card.name} · {card.description}")
            status.setText("\n".join(result.warnings))
            confirm_button.setEnabled(True)

        def _confirm_and_start() -> None:
            try:
                creation_session.confirm()
                session = creation_session.start()
                self._attach_roleplay_session(session)
            except Exception as error:
                status.setText(f"无法启动世界：{error}")
                return
            dialog.accept()

        generate_button.clicked.connect(_generate)
        confirm_button.clicked.connect(_confirm_and_start)
        return dialog

    def open_ai_world_creation(self) -> None:
        if self.game_launcher is None:
            return
        try:
            dialog = self._create_ai_world_creation_dialog()
        except Exception as error:
            self.append_system_message(f"无法创建世界：{error}")
            return
        dialog.exec()

    def start_new_game(self, scenario_id: str):
        if self.game_launcher is None:
            raise RuntimeError("GameLauncher has not been configured.")
        session = self.game_launcher.start_scenario(scenario_id)
        return self._attach_roleplay_session(session)

    def _attach_roleplay_session(self, session):
        from cognitive_sandbox.presentation.ui_runtime import UIRuntime

        self.current_session = session
        UIRuntime(self, session)
        return session

    def append_narrative_event(self, event: _NarrativeEvent) -> None:
        if not isinstance(event, _NarrativeEvent):
            raise TypeError("event must be a NarrativeEvent")
        participants = ", ".join(event.participants)
        detail = f"<br><small>{_html_escape(participants)}</small>" if participants else ""
        self.narrative_display.append(
            f"<p><b>{_html_escape(event.title)}</b><br>{_html_escape(event.description)}{detail}</p>"
        )

    def append_dialogue_line(self, line: _DialogueLine) -> None:
        if not isinstance(line, _DialogueLine):
            raise TypeError("line must be a DialogueLine")
        emotion = f" <small>({_html_escape(line.emotion_hint)})</small>" if line.emotion_hint else ""
        self.narrative_display.append(
            f"<p><b>{_html_escape(line.speaker_id)}{emotion}</b><br>{_html_escape(line.text)}</p>"
        )

    def append_system_message(self, message: str) -> None:
        if not isinstance(message, str) or not message.strip():
            raise ValueError("message must not be empty")
        self.narrative_display.append(f"<p><i>{_html_escape(message.strip())}</i></p>")

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
