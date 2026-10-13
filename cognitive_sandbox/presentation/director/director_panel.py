from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTextBrowser, QVBoxLayout, QWidget

from cognitive_sandbox.director.director_intent import DirectorIntent, DirectorIntentType
from .director_view_model import DirectorViewModel
from .constraint_editor import ConstraintEditor


class DirectorPanel(QWidget):
    result_ready = Signal(object)

    QUICK_OPTIONS = (
        ("促进角色相遇", DirectorIntentType.CHARACTER_MEETING),
        ("推动角色关系", DirectorIntentType.RELATIONSHIP_DEVELOPMENT),
        ("引导角色登场", DirectorIntentType.CHARACTER_ENTRY),
        ("推进调查线程", DirectorIntentType.THREAD_PROGRESS),
        ("增加冲突", DirectorIntentType.WORLD_TENSION),
        ("提升危机", DirectorIntentType.WORLD_TENSION),
        ("增加异常线索", DirectorIntentType.CUSTOM_DIRECTION),
    )

    def __init__(self, session=None, parent=None):
        super().__init__(parent)
        self.setObjectName("directorPanel")
        self.session = session
        self.view_model = DirectorViewModel()
        layout = QVBoxLayout(self)
        title = QLabel("导演模式 · 叙事方向", self)
        title.setObjectName("directorTitle")
        layout.addWidget(title)
        self.world_summary = QLabel("尚未进入世界", self)
        self.world_summary.setObjectName("directorWorldSummary")
        layout.addWidget(self.world_summary)
        row = QHBoxLayout()
        self.target_selector = QComboBox(self)
        self.target_selector.setObjectName("directorTargetSelector")
        self.target_selector.addItem("不指定角色", None)
        row.addWidget(self.target_selector)
        self.partner_selector = QComboBox(self)
        self.partner_selector.setObjectName("directorPartnerSelector")
        self.partner_selector.addItem("第二名角色（可选）", None)
        row.addWidget(self.partner_selector)
        self.direction_input = QLineEdit(self)
        self.direction_input.setObjectName("directorDirectionInput")
        self.direction_input.setPlaceholderText("你希望世界向什么方向发展？")
        row.addWidget(self.direction_input, 1)
        self.submit_button = QPushButton("生成导演目标", self)
        self.submit_button.setObjectName("directorSubmitButton")
        self.submit_button.clicked.connect(self.submit_text)
        row.addWidget(self.submit_button)
        layout.addLayout(row)
        quick = QGridLayout()
        self.quick_buttons = []
        for index, (label, intent_type) in enumerate(self.QUICK_OPTIONS):
            button = QPushButton(label, self)
            button.setObjectName(f"directorQuick{index}")
            button.clicked.connect(lambda _checked=False, kind=intent_type, desc=label: self.submit_quick(kind, desc))
            quick.addWidget(button, index // 4, index % 4)
            self.quick_buttons.append(button)
        layout.addLayout(quick)
        self.result_status = QLabel("导演目标会作为软约束等待因果条件，不直接改变世界。", self)
        self.result_status.setObjectName("directorResultStatus")
        layout.addWidget(self.result_status)
        self.path_view = QTextBrowser(self)
        self.path_view.setObjectName("directorPathView")
        self.path_view.setMaximumHeight(170)
        layout.addWidget(self.path_view)
        self.constraint_editor = ConstraintEditor(parent=self)
        self.constraint_editor.setObjectName("directorConstraintEditor")
        layout.addWidget(self.constraint_editor)
        self.set_session(session)

    def set_session(self, session):
        self.session = session
        self.target_selector.clear()
        self.target_selector.addItem("不指定角色", None)
        self.partner_selector.clear()
        self.partner_selector.addItem("第二名角色（可选）", None)
        if session is not None:
            for context in getattr(session, "agent_contexts", ()):
                self.target_selector.addItem(context.character_state.name, context.character_id)
                self.partner_selector.addItem(context.character_state.name, context.character_id)
            world_name = getattr(getattr(session, "scenario_content", None), "world_document", None)
            world_name = getattr(world_name, "name", None) or getattr(getattr(session, "scenario", None), "name", "当前世界")
            clock = getattr(getattr(session.executor, "world_clock", None), "current_time", None)
            current_time = clock().strftime("%Y-%m-%d %H:%M") if callable(clock) else "时间待推进"
            threads = getattr(getattr(session, "narrative_state", None), "threads", ())
            self.world_summary.setText(f"{world_name} · {current_time} · 剧情线程 {len(threads)} 条")
        else:
            self.world_summary.setText("尚未进入世界")
        available = session is not None and getattr(session, "director_manager", None) is not None
        self.constraint_editor.set_manager(getattr(session, "director_manager", None) if session is not None else None)
        self.direction_input.setEnabled(available)
        self.submit_button.setEnabled(available)
        for button in self.quick_buttons:
            button.setEnabled(available)

    def submit_text(self):
        if self.session is None or self.session.director_manager is None:
            return None
        text = self.direction_input.text().strip()
        if not text:
            self.result_status.setText("请先描述一个叙事方向。")
            return None
        result = self.session.director_manager.submit_text(text)
        self.direction_input.clear()
        self.show_result(result)
        return result

    def submit_quick(self, intent_type, description):
        if self.session is None or self.session.director_manager is None:
            return None
        target = self.target_selector.currentData()
        if intent_type is DirectorIntentType.CHARACTER_MEETING:
            partner = self.partner_selector.currentData()
            if target and partner and partner != target:
                target = f"{target},{partner}"
        intent = DirectorIntent(intent_type, target, description, .65)
        result = self.session.director_manager.submit_intent(intent)
        self.show_result(result)
        return result

    def show_result(self, result):
        view = self.view_model.present(result)
        self.result_status.setText(f"{view['status']} · {view['explanation']}")
        blocks = []
        for index, path in enumerate(view["paths"], 1):
            steps = " → ".join(path["steps"])
            blocks.append(f"{index}. {path['title']}  评分 {path['score']:.2f}\n{steps}\n{path['rationale']}")
        self.path_view.setPlainText("\n\n".join(blocks) or "当前没有可评估路径。")
        self.result_ready.emit(result)
