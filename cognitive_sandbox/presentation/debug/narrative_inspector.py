from __future__ import annotations

from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget


class NarrativeInspector(QWidget):
    """Read-only diagnostic view of presence, motives, story threads and candidates."""

    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session
        self.tree = QTreeWidget(self)
        self.tree.setObjectName("narrativeInspectorTree")
        self.tree.setHeaderLabels(("叙事状态", "详情"))
        self.tree.setEditTriggers(QTreeWidget.EditTrigger.NoEditTriggers)
        layout = QVBoxLayout(self)
        layout.addWidget(self.tree)
        self.refresh()

    def snapshot(self):
        rows = []
        pressure = getattr(self.session, "narrative_pressure", None)
        if pressure is not None:
            rows.append(("剧情压力", f"紧迫度 {pressure.urgency:.2f} · 危险 {pressure.danger:.2f} · 未解决 {pressure.unresolved_degree:.2f} · {pressure.trend}"))
        for presence in getattr(getattr(self.session, "presence_manager", None), "presences", ()):
            rows.append((f"出场：{presence.character_id}", f"{presence.availability.value} · 地点 {presence.current_location or '未指定'}"))
        for motivation in getattr(getattr(self.session, "motivation_manager", None), "motivations", ()):
            view = motivation.view_for(motivation.character_id, privileged=True)
            rows.append((f"动机：{motivation.character_id}",
                         f"公开目标 {view.public_goal}；深层目标 {view.hidden_goal}；核心驱力 {view.core_drive}；恐惧 {view.fear}；价值冲突 {view.value_conflict}"))
        state = getattr(self.session, "narrative_state", None)
        for thread in getattr(state, "threads", ()):
            rows.append((f"线程：{thread.title}", f"{thread.status.value} · 进度 {thread.progress:.0%} · 压力 {thread.pressure:.2f} · 冲突来源 {', '.join(thread.conflict_sources)}"))
        for event in tuple(getattr(self.session, "candidate_events", ())):
            rows.append((f"候选事件：{event.event_type}", f"参与者 {', '.join(event.participants)} · 条件 {', '.join(event.conditions)} · 来源 {', '.join(event.source_conflicts)} · {event.rationale}"))
        for constraint in tuple(getattr(self.session, "narrative_constraints", ())):
            rows.append((f"导演约束：{constraint.target}", f"{constraint.objective} · 优先级 {constraint.priority} · 限制 {', '.join(constraint.constraints)}"))
        return tuple(rows)

    def refresh(self):
        self.tree.clear()
        rows = self.snapshot()
        for label, details in rows:
            self.tree.addTopLevelItem(QTreeWidgetItem((label, details)))
        return rows
