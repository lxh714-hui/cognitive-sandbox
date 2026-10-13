from __future__ import annotations

from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget


class DirectorInspector(QWidget):
    """Read-only summary of submitted soft goals and candidate causal routes."""

    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session
        self.tree = QTreeWidget(self)
        self.tree.setObjectName("directorInspectorTree")
        self.tree.setHeaderLabels(("导演目标", "状态 / 依据"))
        self.tree.setEditTriggers(QTreeWidget.EditTrigger.NoEditTriggers)
        layout = QVBoxLayout(self)
        layout.addWidget(self.tree)
        self.refresh()

    def snapshot(self):
        manager = getattr(self.session, "director_manager", None)
        if manager is None:
            return ()
        rows = []
        for result in manager.history:
            threads = ", ".join(result.affected_threads) or "尚未关联现有线程"
            kind = result.constraint.constraint_type.value
            strength = result.constraint.strength.value
            rows.append((result.intent.description,
                         f"{result.constraint.status.value} · 类型：{kind} · 来源：{result.constraint.source} · "
                         f"强度：{strength} · 影响线程：{threads} · {result.explanation}"))
            for path in result.paths:
                rows.append((f"候选路径：{path.title}",
                             f"评分 {path.score:.2f} · 约束影响 {path.constraint_score:+.2f} · "
                             f"{' → '.join(path.steps)} · {path.rationale}"))
            if not result.paths:
                rows.append(("当前阻碍", "暂时没有符合因果条件的候选路径。"))
        return tuple(rows)

    def refresh(self):
        self.tree.clear()
        rows = self.snapshot()
        for label, details in rows:
            self.tree.addTopLevelItem(QTreeWidgetItem((label, details)))
        return rows
