from __future__ import annotations

from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget


class DevelopmentInspector(QWidget):
    """Read-only view of event-backed long-term character tendencies."""

    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session
        self.tree = QTreeWidget(self)
        self.tree.setHeaderLabels(("角色成长记录", "变化"))
        self.tree.setEditTriggers(QTreeWidget.EditTrigger.NoEditTriggers)
        layout = QVBoxLayout(self)
        layout.addWidget(self.tree)
        self.refresh()

    def snapshot(self):
        engine = getattr(self.session, "development_engine", None)
        if engine is None:
            return ()
        return tuple(record for state in engine.states.values() for record in state.records)

    def refresh(self):
        self.tree.clear()
        for record in self.snapshot():
            item = QTreeWidgetItem((record.character_id, f"{record.change_type.value}: {record.before} → {record.after} · {record.source_event}"))
            self.tree.addTopLevelItem(item)
        return self.snapshot()
