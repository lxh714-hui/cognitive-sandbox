from __future__ import annotations

from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget


class EventViewer(QWidget):
    """Read-only view of recorded events and their resulting state changes."""

    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session
        self.tree = QTreeWidget(self)
        self.tree.setObjectName("eventViewerTree")
        self.tree.setHeaderLabels(("事件 / 变化", "详情"))
        self.tree.setEditTriggers(QTreeWidget.EditTrigger.NoEditTriggers)
        self.tree.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection)
        layout = QVBoxLayout(self)
        layout.addWidget(self.tree)
        self.refresh()

    def snapshot(self):
        executor = self.session.executor
        timeline = getattr(executor, "event_timeline", None)
        engine = getattr(executor, "world_evolution_engine", None)
        records = tuple(getattr(timeline, "events", ()))
        changes = tuple(getattr(engine, "state_changes", ()))
        by_event = {}
        for change in changes:
            if change.event_id:
                by_event.setdefault(change.event_id, []).append(change)
        return tuple((record, tuple(by_event.get(record.event_id, ()))) for record in records)

    def refresh(self):
        self.tree.clear()
        snapshot = self.snapshot()
        for record, changes in snapshot:
            title = record.metadata.get("description") or record.event_type
            event_item = QTreeWidgetItem((str(title), f"{record.timestamp} · {record.event_type} · {record.event_id}"))
            self.tree.addTopLevelItem(event_item)
            for change in changes:
                detail = f"{change.target_type}:{change.target_id}.{change.field}"
                event_item.addChild(QTreeWidgetItem((detail, f"{change.old_value!s} → {change.new_value!s} · {change.reason}")))
        return snapshot
