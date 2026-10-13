from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QPushButton, QTabWidget, QTextBrowser, QVBoxLayout, QWidget

from cognitive_sandbox.presentation.debug.debug_report import DebugReportBuilder
from cognitive_sandbox.presentation.debug.event_viewer import EventViewer
from cognitive_sandbox.presentation.debug.goal_inspector import GoalInspector
from cognitive_sandbox.presentation.debug.knowledge_inspector import KnowledgeInspector
from cognitive_sandbox.presentation.debug.npc_inspector import NpcInspector
from cognitive_sandbox.presentation.debug.world_inspector import WorldInspector
from cognitive_sandbox.presentation.debug.narrative_inspector import NarrativeInspector
from cognitive_sandbox.presentation.debug.emotion_inspector import EmotionInspector
from cognitive_sandbox.presentation.debug.director_inspector import DirectorInspector
from cognitive_sandbox.presentation.debug.authority_inspector import AuthorityInspector
from cognitive_sandbox.presentation.debug.cognition_inspector import CognitionInspector


class DebugDashboard(QWidget):
    """Tabbed, read-only visualization of the active simulation runtime."""

    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session
        self.tabs = QTabWidget(self)
        self.world_inspector = WorldInspector(session, self.tabs)
        self.event_viewer = EventViewer(session, self.tabs)
        self.npc_inspector = NpcInspector(session, self.tabs)
        self.goal_inspector = GoalInspector(session, self.tabs)
        self.knowledge_inspector = KnowledgeInspector(session, self.tabs)
        self.narrative_inspector = NarrativeInspector(session, self.tabs)
        self.emotion_inspector = EmotionInspector(session, self.tabs)
        self.director_inspector = DirectorInspector(session, self.tabs)
        self.authority_inspector = AuthorityInspector(session, self.tabs)
        self.cognition_inspector = CognitionInspector(session, self.tabs)
        self.report_view = QTextBrowser(self.tabs)
        self.report_view.setObjectName("debugReportView")
        self.report_view.setOpenExternalLinks(False)
        for widget, label in (
            (self.world_inspector, "世界"),
            (self.event_viewer, "事件"),
            (self.npc_inspector, "NPC"),
            (self.goal_inspector, "目标"),
            (self.knowledge_inspector, "角色知识"),
            (self.narrative_inspector, "剧情状态"),
            (self.emotion_inspector, "角色情绪"),
            (self.director_inspector, "导演目标"),
            (self.authority_inspector, "角色权限"),
            (self.cognition_inspector, "角色认知"),
            (self.report_view, "诊断报告"),
        ):
            self.tabs.addTab(widget, label)
        self.refresh_button = QPushButton("刷新", self)
        self.refresh_button.clicked.connect(self.refresh)
        layout = QVBoxLayout(self)
        layout.addWidget(self.tabs)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(self.refresh_button)
        layout.addLayout(buttons)
        self.refresh()

    def refresh(self):
        self.world_inspector.refresh()
        self.event_viewer.refresh()
        self.npc_inspector.refresh()
        self.goal_inspector.refresh()
        knowledge_character = self.knowledge_inspector.character_selector.currentData()
        self.knowledge_inspector.refresh()
        self.narrative_inspector.refresh()
        self.emotion_inspector.refresh()
        self.director_inspector.refresh()
        self.authority_inspector.refresh()
        self.cognition_inspector.refresh()
        report = DebugReportBuilder().build(
            self.session,
            character_id=knowledge_character if isinstance(knowledge_character, str) else None,
            knowledge_query=self.knowledge_inspector.query_input.text(),
        )
        self.report_view.setPlainText(report.text)
        return report
