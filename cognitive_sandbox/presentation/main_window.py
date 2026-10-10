from __future__ import annotations

from PySide6.QtCore import QObject, QSettings, Qt, QThread, Signal, Slot
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget, QMainWindow, QSplitter, QSplitterHandle,
    QPushButton, QSizePolicy, QTextBrowser, QVBoxLayout, QWidget,
)

from cognitive_sandbox.application.service import SandboxService
from cognitive_sandbox.domain.models import Agent, CognitiveMemory, ConversationEvent, World
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
        input_row.addWidget(self.input, 1)
        input_row.addWidget(self.send_button)
        left_layout.addLayout(input_row)
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
    def _turn_finished(self, _reply: str) -> None:
        self._load_history()
        self.status.setText(f"{self.service.provider.label}  ·  对话保存在本地")
        self.send_button.setEnabled(True)
        self.input.setFocus()

    @Slot(str)
    def _turn_failed(self, message: str) -> None:
        self.status.setText(f"生成失败：{message}（检查 Ollama 配置后可重试）")
        self.send_button.setEnabled(True)
        self.input.setFocus()

    @Slot()
    def _clear_worker(self) -> None:
        if self._worker is not None:
            self._worker.deleteLater()
        if self._thread is not None:
            self._thread.deleteLater()
        self._worker = None
        self._thread = None


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


