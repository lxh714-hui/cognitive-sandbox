from __future__ import annotations

from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget

from cognitive_sandbox.emotion.emotional_state import EMOTION_FIELDS


class EmotionInspector(QWidget):
    """Read-only view of continuous affect and its event trace."""

    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session
        self.tree = QTreeWidget(self)
        self.tree.setObjectName("emotionInspectorTree")
        self.tree.setHeaderLabels(("角色 / 情绪", "当前值 / 来源"))
        self.tree.setEditTriggers(QTreeWidget.EditTrigger.NoEditTriggers)
        layout = QVBoxLayout(self)
        layout.addWidget(self.tree)
        self.refresh()

    def snapshot(self):
        engine = getattr(self.session, "emotion_engine", None)
        if engine is None:
            return ()
        rows = []
        names = {
            context.character_id: context.character_state.name
            for context in getattr(self.session, "agent_contexts", ())
        }
        states = dict(engine.states)
        for character_id in names:
            states.setdefault(character_id, engine.state_for(character_id))
        for character_id, state in sorted(states.items()):
            label = names.get(character_id, character_id)
            for field in EMOTION_FIELDS:
                value = getattr(state, field)
                if value > 0:
                    rows.append((f"{label} · {field}", f"{value:.0%}"))
        for event in engine.history[-20:]:
            label = names.get(event.character_id, event.character_id)
            rows.append((f"变化 · {label} · {event.emotion_type}",
                         f"{event.delta:+.0%} · {event.reason} · {event.source_event_id}"))
        return tuple(rows)

    def refresh(self):
        self.tree.clear()
        rows = self.snapshot()
        for label, details in rows:
            self.tree.addTopLevelItem(QTreeWidgetItem((label, details)))
        return rows
