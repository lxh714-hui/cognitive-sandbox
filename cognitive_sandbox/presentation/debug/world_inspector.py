from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget


class WorldInspector(QWidget):
    """Read-only snapshot of world, locations, resources, and agent status."""

    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session
        self.tree = QTreeWidget(self)
        self.tree.setObjectName("worldInspectorTree")
        self.tree.setHeaderLabels(("项目", "当前值"))
        self.tree.setEditTriggers(QTreeWidget.EditTrigger.NoEditTriggers)
        self.tree.setSelectionMode(QTreeWidget.SelectionMode.NoSelection)
        layout = QVBoxLayout(self)
        layout.addWidget(self.tree)
        self.refresh()

    def snapshot(self):
        session = self.session
        executor = session.executor
        content = getattr(session, "scenario_content", None)
        document = getattr(content, "world_document", None)
        scenario = getattr(session, "scenario", None)
        world_name = getattr(document, "name", None) or getattr(scenario, "name", None) or session.world_instance_id or "World"
        clock = getattr(executor, "world_clock", None)
        now = clock.current_time().isoformat() if clock is not None else "unavailable"
        state = session.world_state if isinstance(session.world_state, Mapping) else {}
        stage = _first(state, "current_stage", "stage", "phase")

        locations = tuple(
            MappingProxyType({
                "id": location.location_id,
                "name": location.name,
                "status": location.status,
                "safety": location.safety,
                "power": location.power,
                "properties": dict(location.properties),
            })
            for location in getattr(getattr(executor, "location_manager", None), "locations", ())
        )
        resources = tuple(
            MappingProxyType({
                "type": item.resource_type,
                "quantity": item.quantity,
                "location_id": item.location_id,
            })
            for item in getattr(getattr(executor, "resource_manager", None), "resources", ())
        )
        characters = []
        minds = getattr(executor, "character_minds", {})
        for context in tuple(getattr(session, "agent_contexts", ())):
            character = context.character_state
            mind = minds.get(context.character_id)
            identity = getattr(mind, "identity", None)
            characters.append(MappingProxyType({
                "id": context.character_id,
                "name": getattr(identity, "name", None) or character.name,
                "role": getattr(identity, "role", None) or character.role,
                "confidence": context.dynamic_state.confidence,
                "stress": context.dynamic_state.stress,
                "motivation": context.dynamic_state.motivation,
            }))
        return MappingProxyType({
            "world_name": world_name,
            "world_id": getattr(executor, "world_id", ""),
            "time": now,
            "stage": str(stage) if stage is not None else "not set",
            "locations": locations,
            "resources": resources,
            "characters": tuple(characters),
        })

    def refresh(self):
        snapshot = self.snapshot()
        self.tree.clear()
        _branch(self.tree, "世界", (
            ("名称", snapshot["world_name"]),
            ("世界 ID", snapshot["world_id"]),
            ("时间", snapshot["time"]),
            ("当前阶段", snapshot["stage"]),
        ))
        _section(self.tree, "地点", snapshot["locations"], lambda row: (
            ("名称", row["name"]), ("ID", row["id"]), ("状态", row["status"]),
            ("安全度", row["safety"]), ("供电", _display(row["power"])),
            ("场景属性", row["properties"]),
        ))
        _section(self.tree, "资源", snapshot["resources"], lambda row: (
            ("类型", row["type"]), ("数量", row["quantity"]),
            ("地点", row["location_id"] or "全世界"),
        ))
        _section(self.tree, "角色", snapshot["characters"], lambda row: (
            ("名称", row["name"]), ("ID", row["id"]), ("身份", row["role"]),
            ("信心", row["confidence"]), ("压力", row["stress"]),
            ("动力", row["motivation"]),
        ))
        return snapshot


def _branch(tree, title, values):
    parent = QTreeWidgetItem((title, ""))
    tree.addTopLevelItem(parent)
    for key, value in values:
        parent.addChild(QTreeWidgetItem((key, str(value))))
    parent.setExpanded(True)
    return parent


def _section(tree, title, rows, fields):
    parent = QTreeWidgetItem((title, str(len(rows))))
    tree.addTopLevelItem(parent)
    for row in rows:
        label = row.get("name", row.get("type", row.get("id", "项目")))
        child = QTreeWidgetItem((str(label), ""))
        parent.addChild(child)
        for key, value in fields(row):
            child.addChild(QTreeWidgetItem((key, _display(value))))
    parent.setExpanded(True)
    return parent


def _first(state, *keys):
    return next((state[key] for key in keys if key in state and state[key] is not None), None)


def _display(value):
    if value is None:
        return "未设置"
    if isinstance(value, bool):
        return "是" if value else "否"
    return str(value)
