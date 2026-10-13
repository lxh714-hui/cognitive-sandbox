from PySide6.QtWidgets import QDialog, QListWidget, QVBoxLayout


class RelationshipInspector(QDialog):
    """Read-only view of relationship stages, source events, and recent memories."""

    def __init__(self, lifecycle_manager, relationship_manager=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("关系检查器")
        self.setObjectName("relationshipInspector")
        self.lifecycle_manager = lifecycle_manager
        self.relationship_manager = relationship_manager or getattr(lifecycle_manager, "relationship_manager", None)
        self.entries = QListWidget(self)
        self.entries.setObjectName("relationshipEntries")
        layout = QVBoxLayout(self)
        layout.addWidget(self.entries)
        self.refresh()

    def refresh(self):
        self.entries.clear()
        memories = self.lifecycle_manager.memories
        transitions = self.lifecycle_manager.transitions
        dynamics_by_pair = {(item.character_a, item.character_b): item
                            for item in self.lifecycle_manager.dynamics}
        for entry in self.lifecycle_manager.stages:
            relation = self.relationship_manager.get_relationship(entry.character_a, entry.character_b)
            dynamics = dynamics_by_pair[(entry.character_a, entry.character_b)]
            lines = [f"{entry.character_a} → {entry.character_b} · {entry.stage.value}",
                     f"信任 {relation.trust:g} · 熟悉 {dynamics.familiarity:.2f} · "
                     f"依赖 {dynamics.dependence:.2f} · 距离 {dynamics.distance:.2f}"]
            recent = [item for item in memories
                      if item.character_a == entry.character_a and item.character_b == entry.character_b][-3:]
            lines.extend(f"经历：{item.memory_type} · 来源 {item.source_event}" for item in recent)
            transition = next((item for item in reversed(transitions)
                               if item.character_a == entry.character_a and item.character_b == entry.character_b), None)
            if transition:
                lines.append(f"阶段变化：{transition.reason} · 来源 {transition.source_event_id}")
            self.entries.addItem("\n".join(lines))
