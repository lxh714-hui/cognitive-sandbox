from PySide6.QtWidgets import QLabel, QListWidget, QVBoxLayout, QWidget


class ConflictView(QWidget):
    """Player-safe view of conflicts the player character is directly involved in."""
    _CAUSES = {
        "goal_conflict": "双方目标之间存在分歧。",
        "resource_conflict": "有限资源影响了相关目标。",
        "information_conflict": "相关人物掌握的信息并不相同。",
        "value_conflict": "相关人物对当前情况有不同理解。",
    }
    _STATUSES = {
        "emerging": "刚刚显现", "active": "正在发展", "escalating": "压力上升",
        "stable": "暂时维持", "resolved": "已解决", "transformed": "已转化",
        "accepted": "已接受", "escalated": "压力上升",
    }

    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session
        self.title = QLabel("当前冲突", self)
        self.items = QListWidget(self)
        layout = QVBoxLayout(self)
        layout.addWidget(self.title)
        layout.addWidget(self.items)
        self.refresh()

    def refresh(self):
        self.items.clear()
        manager = getattr(self.session, "conflict_manager", None)
        player_id = getattr(self.session, "player_id", None)
        if manager is None or not player_id:
            return ()
        names = getattr(self.session, "identity_manager", None)
        shown = []
        for conflict in manager.active_conflicts:
            # The story surface does not reveal conflicts that have not reached
            # the player through participation or their own visible experience.
            if player_id not in conflict.participants:
                continue
            kind = getattr(conflict.conflict_type, "value", conflict.conflict_type)
            status = getattr(conflict.status, "value", conflict.status)
            other_names = []
            for character_id in conflict.participants:
                if character_id == player_id:
                    continue
                display = names.display_name_for(character_id, "") if names is not None else ""
                if display:
                    other_names.append(display)
            participants = "、".join(other_names)
            cause = self._CAUSES.get(kind, "当前处境中存在尚未解决的阻碍。")
            line = f"{cause} {participants + '也受到影响。' if participants else ''}（{self._STATUSES.get(status, '正在发展')}）"
            self.items.addItem(line)
            shown.append(line)
        self.setVisible(bool(shown))
        return tuple(shown)
