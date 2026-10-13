from __future__ import annotations

from types import MappingProxyType

from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget


class NpcInspector(QWidget):
    """Read-only character mind and live state inspector, excluding player."""

    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session
        self.tree = QTreeWidget(self)
        self.tree.setObjectName("npcInspectorTree")
        self.tree.setHeaderLabels(("NPC", "当前状态"))
        self.tree.setEditTriggers(QTreeWidget.EditTrigger.NoEditTriggers)
        layout = QVBoxLayout(self)
        layout.addWidget(self.tree)
        self.refresh()

    def snapshot(self):
        executor = self.session.executor
        minds = getattr(executor, "character_minds", {})
        goals = getattr(executor, "goal_manager", None)
        result = []
        for context in tuple(getattr(self.session, "agent_contexts", ())):
            if context.character_id == self.session.player_id:
                continue
            mind = minds.get(context.character_id)
            identity = getattr(mind, "identity", None)
            personality = getattr(mind, "personality", None)
            result.append(MappingProxyType({
                "character_id": context.character_id,
                "name": getattr(identity, "name", None) or context.character_state.name,
                "role": getattr(identity, "role", None) or context.character_state.role,
                "traits": tuple(getattr(personality, "traits", context.character_state.traits)),
                "goals": tuple(goals.for_character(context.character_id)) if goals is not None else (),
                "confidence": context.dynamic_state.confidence,
                "stress": context.dynamic_state.stress,
                "motivation": context.dynamic_state.motivation,
            }))
        return tuple(result)

    def refresh(self):
        self.tree.clear()
        snapshot = self.snapshot()
        for npc in snapshot:
            item = QTreeWidgetItem((npc["name"], npc["role"]))
            self.tree.addTopLevelItem(item)
            for key, value in (
                ("ID", npc["character_id"]),
                ("性格特征", "、".join(npc["traits"])),
                ("信心", npc["confidence"]),
                ("压力", npc["stress"]),
                ("动力", npc["motivation"]),
            ):
                item.addChild(QTreeWidgetItem((key, str(value))))
            for goal in npc["goals"]:
                status = f"{goal.status} · {goal.progress:.0%} · priority {goal.priority:.2f}"
                item.addChild(QTreeWidgetItem((f"目标：{goal.description}", status)))
            item.setExpanded(True)
        return snapshot
