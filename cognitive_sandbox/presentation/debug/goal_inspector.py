from __future__ import annotations

from types import MappingProxyType

from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget


class GoalInspector(QWidget):
    """Read-only tree view of goal ownership, dependencies, and progress."""

    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session
        self.tree = QTreeWidget(self)
        self.tree.setObjectName("goalInspectorTree")
        self.tree.setHeaderLabels(("目标树", "进度 / 状态"))
        self.tree.setEditTriggers(QTreeWidget.EditTrigger.NoEditTriggers)
        layout = QVBoxLayout(self)
        layout.addWidget(self.tree)
        self.refresh()

    def snapshot(self):
        manager = getattr(self.session.executor, "goal_manager", None)
        lifecycle = getattr(self.session, "goal_lifecycle_manager", None)
        goals = tuple(getattr(manager, "goals", ()))
        by_id = {goal.goal_id: goal for goal in goals}
        rows = []
        roots = sorted((goal for goal in goals if goal.parent_goal_id is None), key=lambda goal: (goal.owner_id, goal.goal_id))
        for root in roots:
            _append_tree(root, by_id, rows, 0, set())
        # Orphaned entries are still visible as diagnostic roots.
        included = {row[0].goal_id for row in rows}
        for goal in sorted(goals, key=lambda item: (item.owner_id, item.goal_id)):
            if goal.goal_id not in included:
                _append_tree(goal, by_id, rows, 0, set())
        return tuple(MappingProxyType({
            "goal_id": goal.goal_id,
            "parent_goal_id": goal.parent_goal_id,
            "owner_id": goal.owner_id,
            "description": goal.description,
            "goal_type": goal.goal_type,
            "priority": goal.priority,
            "progress": goal.progress,
            "status": goal.status,
            "lifecycle_state": (lifecycle.state_for(goal.goal_id).state.value
                                if lifecycle is not None and lifecycle.state_for(goal.goal_id) is not None
                                else goal.status.upper()),
            "depth": depth,
        }) for goal, depth in rows)

    def refresh(self):
        self.tree.clear()
        snapshot = self.snapshot()
        items = {}
        for row in snapshot:
            label = f"{row['description']} [{row['goal_type']}] · {row['owner_id']}"
            item = QTreeWidgetItem((label, f"{row['progress']:.0%} · {row['lifecycle_state']} · priority {row['priority']:.2f}"))
            parent = items.get(row["parent_goal_id"])
            if parent is None:
                self.tree.addTopLevelItem(item)
            else:
                parent.addChild(item)
            items[row["goal_id"]] = item
            item.setExpanded(True)
        return snapshot


def _append_tree(goal, by_id, rows, depth, visited):
    if goal.goal_id in visited:
        return
    visited.add(goal.goal_id)
    rows.append((goal, depth))
    for child_id in goal.subgoals:
        child = by_id.get(child_id)
        if child is not None:
            _append_tree(child, by_id, rows, depth + 1, visited)
