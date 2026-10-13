from __future__ import annotations

from collections import defaultdict

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QListWidget, QListWidgetItem, QVBoxLayout, QWidget


class WorldChroniclePanel(QWidget):
    """Read-only player-facing timeline of events and deterministic state changes."""

    _EVENT_TEXT = {
        "npc_patrolled": "有人巡查了周边区域。",
        "wait_elapsed": "你等待了一段时间。",
    }
    _FIELD_TEXT = {
        "safety": "安全度",
        "power": "供电",
        "status": "地点状态",
        "quantity": "资源数量",
        "progress": "目标进度",
    }
    _TARGET_TEXT = {"resource": "资源", "goal": "目标", "location": "地点"}

    def __init__(self, event_timeline=None, state_changes=(), *, location_manager=None, goal_manager=None, parent=None):
        super().__init__(parent)
        self.event_timeline = event_timeline
        self.state_changes = tuple(state_changes)
        self.location_manager = location_manager
        self.goal_manager = goal_manager
        self.title_label = QLabel("世界编年史", self)
        self.entries_list = QListWidget(self)
        self.entries_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self.entries_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        layout = QVBoxLayout(self)
        layout.addWidget(self.title_label)
        layout.addWidget(self.entries_list)
        self.refresh()

    def refresh(self):
        self.entries_list.clear()
        records = tuple(getattr(self.event_timeline, "events", ()))
        changes = tuple(self.state_changes)
        grouped = defaultdict(list)
        for change in changes:
            if change.event_id:
                grouped[change.event_id].append(change)
        for record in records:
            text = self._event_text(record)
            details = [self._change_text(change) for change in grouped.get(record.event_id, ())]
            stamp = record.timestamp
            rendered = f"{stamp}  {text}" if stamp else text
            if details:
                rendered += "\n" + "\n".join(details)
            item = QListWidgetItem(rendered)
            item.setData(Qt.ItemDataRole.UserRole, record.event_id)
            self.entries_list.addItem(item)
        return tuple(self.entries_list.item(index).text() for index in range(self.entries_list.count()))

    def set_state_changes(self, state_changes):
        self.state_changes = tuple(state_changes)
        return self.refresh()

    def _event_text(self, record):
        description = record.metadata.get("description")
        if isinstance(description, str) and description.strip():
            # Action event descriptions are authored presentation text.
            return description.strip()
        return self._EVENT_TEXT.get(record.event_type, "世界中发生了一件新事情。")

    def _change_text(self, change):
        field = self._FIELD_TEXT.get(change.field, "状态")
        if change.target_type == "location":
            location = self.location_manager.get(change.target_id) if self.location_manager else None
            target = location.name if location else self._TARGET_TEXT.get(change.target_id, "某处")
        elif change.target_type == "goal":
            goal = self.goal_manager.by_id(change.target_id) if self.goal_manager else None
            target = goal.description if goal else "角色目标"
        elif change.target_type == "resource":
            target = "资源"
        else:
            target = self._TARGET_TEXT.get(change.target_type, "世界")
        return f"世界变化：{target}的{field} {self._render(change.old_value)} → {self._render(change.new_value)}。"

    @staticmethod
    def _render(value):
        if value is None:
            return "无"
        if isinstance(value, bool):
            return "已恢复" if value else "未恢复"
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        return str(value)
