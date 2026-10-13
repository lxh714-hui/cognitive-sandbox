from PySide6.QtWidgets import QTextBrowser, QVBoxLayout, QWidget


class CognitionInspector(QWidget):
    """Read-only display of per-character cognitive profiles and recent thoughts."""

    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session
        self.view = QTextBrowser(self)
        self.view.setObjectName("cognitionInspectorView")
        self.view.setOpenExternalLinks(False)
        layout = QVBoxLayout(self)
        layout.addWidget(self.view)
        self.refresh()

    def refresh(self):
        engine = getattr(getattr(self.session, "executor", None), "cognitive_engine", None)
        if engine is None:
            self.view.setPlainText("当前会话没有认知状态记录。")
            return
        lines = []
        for character in getattr(self.session, "agent_contexts", ()):
            character_id = character.character_id
            style = engine.style_for(character_id)
            reasoning = engine.reasoning_for(character_id)
            percent = lambda value: f"{round(value * 100)}%"
            lines.extend((
                f"角色：{character.character_state.name}",
                f"认知风格：分析 {percent(style.analytical)} · 直觉 {percent(style.intuitive)} · "
                f"怀疑 {percent(style.suspicious)} · 现实主义 {percent(style.pragmatic)}",
                f"推理深度：{percent(reasoning.reasoning_depth)}",
            ))
            thoughts = engine.thoughts.get(character_id, ())
            if thoughts:
                thought = thoughts[-1]
                lines.extend((f"最近解释（事件 {thought.source_event}）：",
                              f"关注：{'、'.join(thought.observation_focus)}",
                              f"判断：{thought.interpretation}"))
            lines.append("")
        self.view.setPlainText("\n".join(lines) or "当前世界没有角色认知记录。")
