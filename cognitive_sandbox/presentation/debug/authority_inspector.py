from PySide6.QtWidgets import QTextBrowser, QVBoxLayout, QWidget

from cognitive_sandbox.authority.authority_level import AuthorityLevel


class AuthorityInspector(QWidget):
    """Read-only view of character authority assignments."""

    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session
        self.view = QTextBrowser(self)
        self.view.setObjectName("authorityInspectorView")
        self.view.setOpenExternalLinks(False)
        layout = QVBoxLayout(self)
        layout.addWidget(self.view)
        self.refresh()

    def refresh(self):
        manager = getattr(self.session, "authority_manager", None)
        if manager is None:
            self.view.setPlainText("当前会话没有权限信息。")
            return
        lines = []
        for context in getattr(self.session, "agent_contexts", ()):
            authority = manager.authority_for(context.character_id)
            if authority is None:
                continue
            name = context.character_state.name
            kind = {
                AuthorityLevel.PLAYER: "Player Character",
                AuthorityLevel.IMPORTANT_CHARACTER: "Important Character",
                AuthorityLevel.BACKGROUND_CHARACTER: "Background Character",
            }.get(authority.authority_level, authority.authority_level.name)
            lines.extend((
                f"角色：{name}",
                f"类型：{kind}",
                f"权限：{authority.authority_level.name}",
                f"可控制：{'YES' if authority.controllable else 'NO'}",
                f"可自主决策：{'YES' if authority.can_make_autonomous_decisions else 'NO'}",
                "",
            ))
        self.view.setPlainText("\n".join(lines) or "当前世界没有角色权限记录。")
